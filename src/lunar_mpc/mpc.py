"""Adaptive, finite-control-set MPC for the discrete LunarLander environment.

Extracted for standalone lunar-mpc on 2026-09-08; evaluator imports changed.

The controller receives observations only. The evaluator below owns simulator
access for disturbances and scoring; it never passes hidden physics to MPC.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time

import numpy as np

DT = 1 / 50
OBS_SCALE = np.array([10, 20 / 3, 5, 7.5, 1, 2.5], dtype=float)


def state_from_obs(obs):
    obs = np.asarray(obs, dtype=float)
    if obs.shape != (8,) or not np.isfinite(obs).all():
        raise ValueError("Expected eight finite LunarLander observation values")
    return obs[:6] * OBS_SCALE


@dataclass
class MPCConfig:
    horizon: int = 16
    hold: int = 4
    beam: int = 32
    adaptive: bool = True
    forgetting: float = 0.99

    def __post_init__(self):
        if min(self.horizon, self.hold, self.beam) < 1:
            raise ValueError("horizon, hold and beam must be positive")
        if not 0 < self.forgetting <= 1:
            raise ValueError("forgetting must be in (0, 1]")


class Dynamics:
    """Planar acceleration model, updated by bounded recursive least squares."""
    def __init__(self, forgetting=0.99):
        # [main acceleration, side acceleration, horizontal bias, vertical bias]
        self.linear = np.array([18., 2.5, 0., 0.])
        # [side angular acceleration, angular bias]
        self.angular = np.array([5., 0.])
        self.p = np.diag([4., 1., 1., 1.])
        self.pa = np.diag([1., .5])
        self.forgetting = forgetting
        self.updates = 0
        self.last_error = 0.

    def predict(self, x, action, dt=DT):
        x = np.asarray(x)
        main = np.asarray(action) == 2
        side = np.where(np.asarray(action) == 1, -1., np.where(np.asarray(action) == 3, 1., 0.))
        s, c = np.sin(x[..., 4]), np.cos(x[..., 4])
        mg, sg, bx, by = self.linear
        ax = -mg * main * s + sg * side * c + bx
        ay = mg * main * c + sg * side * s - 10 + by
        aw = -self.angular[0] * side + self.angular[1]
        out = x.copy()
        out[..., 2] += dt * ax
        out[..., 3] += dt * ay
        out[..., 5] += dt * aw
        out[..., 0] += dt * out[..., 2]
        out[..., 1] += dt * out[..., 3]
        out[..., 4] += dt * out[..., 5]
        return out

    def _fit(self, theta, covariance, phi, target):
        projected = covariance @ phi
        gain = projected / (self.forgetting + phi @ projected)
        theta += gain * (target - phi @ theta)
        covariance[:] = (covariance - np.outer(gain, projected)) / self.forgetting
        covariance[:] = (covariance + covariance.T) / 2

    def observe(self, before, action, after, learn=True):
        x, nxt = state_from_obs(before), state_from_obs(after)
        prediction = self.predict(x, action)
        self.last_error = float(np.linalg.norm(nxt[[2, 3, 5]] - prediction[[2, 3, 5]]))
        if not learn:
            return
        # Contact impulses are not evidence of changed airborne engine strength.
        if np.any(np.asarray(before)[6:]) or np.any(np.asarray(after)[6:]):
            return
        acceleration = (nxt[[2, 3, 5]] - x[[2, 3, 5]]) / DT
        if np.max(np.abs(acceleration)) > 60:
            return
        main, side = float(action == 2), float(action == 3) - float(action == 1)
        s, c = np.sin(x[4]), np.cos(x[4])
        self._fit(self.linear, self.p, np.array([-main*s, side*c, 1., 0.]), acceleration[0])
        self._fit(self.linear, self.p, np.array([main*c, side*s, 0., 1.]), acceleration[1]+10)
        self._fit(self.angular, self.pa, np.array([-side, 1.]), acceleration[2])
        self.linear[:] = np.clip(self.linear, [5., .3, -4., -4.], [35., 6., 4., 4.])
        self.angular[:] = np.clip(self.angular, [1., -2.], [10., 2.])
        self.updates += 1


class AdaptiveMPC:
    def __init__(self, config=None):
        self.cfg = config or MPCConfig()
        self.model = Dynamics(self.cfg.forgetting)
        self.last_plan = []
        self.last_prediction = []
        self.last_cost = 0.

    def observe(self, before, action, after):
        self.model.observe(before, action, after, learn=self.cfg.adaptive)

    def advance(self, states, actions, settled):
        predicted = self.model.predict(states, actions, DT*self.cfg.hold)
        predicted[settled] = states[settled]
        # Approximate safe contact as absorbing. This is a terminal model, not
        # a certificate that Box2D's articulated legs will settle successfully.
        landed = settled | ((predicted[:, 1] <= 0) & (np.abs(predicted[:, 0]) < 1.1)
                            & (np.abs(predicted[:, 2]) < .7) & (predicted[:, 3] > -1.)
                            & (np.abs(predicted[:, 4]) < .15) & (np.abs(predicted[:, 5]) < .3))
        predicted[landed, 1:] = 0
        return predicted, landed

    def cost(self, x):
        px, y, vx, vy, angle, omega = x.T
        vx_ref = np.clip(-.7 * px, -3, 3)
        angle_ref = np.clip(.16 * (vx - vx_ref), -.5, .5)
        clearance = y - .5*np.maximum(0, np.abs(px)-1.)
        vy_ref = np.clip(-.8 * clearance, -2.5, 1.)
        vy_ref = np.where((np.abs(px) < 1.) & (y < 1.), -.4, vy_ref)
        # Lower estimated thrust means start braking higher. The factor .7 is
        # a design margin, not a statistically certified uncertainty bound.
        upward = np.maximum(.2, .7*self.model.linear[0]*np.cos(angle)-10+self.model.linear[3])
        braking_speed = np.sqrt(2*upward*np.maximum(.05, clearance))
        vy_ref = np.maximum(vy_ref, -braking_speed)
        cost = (.2*px**2 + .4*(vx-vx_ref)**2 + 2*(vy-vy_ref)**2
                + 25*(angle-angle_ref)**2 + 2*(omega+2*(angle-angle_ref))**2)
        # Soft approach envelope and tilt limits; these are penalties, not a
        # proof of collision avoidance or recursive feasibility.
        cost += 300 * np.maximum(0, .5*(np.abs(px)-1.1) - y)**2
        cost += 100 * np.maximum(0, np.abs(angle)-.65)**2
        cost += 1000 * np.maximum(0, -y-.05)**2
        return cost

    def act(self, obs):
        state = state_from_obs(obs)
        if np.any(np.asarray(obs)[6:]):
            self.last_plan, self.last_cost = [0], 0.
            self.last_prediction = [state.tolist()]
            return 0
        states = state[None]
        settled = np.zeros(1, dtype=bool)
        costs = np.zeros(1)
        paths = np.zeros((1, 0), dtype=int)
        for _ in range(self.cfg.horizon):
            actions = np.tile(np.arange(4), len(states))
            states, settled = self.advance(np.repeat(states, 4, axis=0), actions, np.repeat(settled, 4))
            costs = np.repeat(costs, 4) + np.where(settled, 0., self.cost(states)) * DT*self.cfg.hold
            costs += .005 * (actions == 2)
            paths = np.column_stack((np.repeat(paths, 4, axis=0), actions))
            keep = np.argsort(costs, kind="stable")[:self.cfg.beam]
            states, costs, paths, settled = states[keep], costs[keep], paths[keep], settled[keep]
        best = int(np.argmin(costs))
        self.last_plan, self.last_cost = paths[best].tolist(), float(costs[best])
        predicted, settled = state[None], np.zeros(1, dtype=bool)
        self.last_prediction = [state.tolist()]
        for action in self.last_plan:
            predicted, settled = self.advance(predicted, np.array([action]), settled)
            self.last_prediction.append(predicted[0].tolist())
        return int(paths[best, 0])


def landing_result(env, terminated, truncated, final_obs):
    """Evaluator-only simulator truth; accumulated reward is not a landing test."""
    u = env.unwrapped
    feet = [u.lander.position.x + sign*2/3*np.cos(u.lander.angle) + .6*np.sin(u.lander.angle)
            for sign in (-1, 1)]
    margin = min(min(feet)-u.helipad_x1, u.helipad_x2-max(feet))
    landed = bool(terminated and not truncated and not u.game_over and not u.lander.awake
                  and all(leg.ground_contact for leg in u.legs) and abs(final_obs[0]) < 1)
    return {"landed": landed, "feet_inside": bool(margin >= 0),
            "pad_margin": float(margin), "passed": bool(landed and margin >= 0),
            "terminated": bool(terminated), "truncated": bool(truncated),
            "rendered_foot_x": [float(x) for x in feet]}


def run_episode(seed, cfg, thrust_scale=1., change_step=100):
    import gymnasium as gym
    from gymnasium.envs.box2d import lunar_lander as LL
    from lunar_mpc.environment import StartPose
    if not 0 < thrust_scale <= 1 or change_step < 0:
        raise ValueError("thrust_scale must be in (0, 1] and change_step nonnegative")
    env = StartPose(gym.make("LunarLander-v3"), 6, .5)
    controller = AdaptiveMPC(cfg)
    obs, info = env.reset(seed=seed)
    total, records, first_contact = 0., [], None
    # This evaluator runs one environment at a time. The temporary, process-local
    # engine constant changes simulator physics, never the controller's model.
    try:
        term = trunc = False
        while not (term or trunc):
            tick = len(records)
            begin = time.perf_counter()
            action = controller.act(obs)
            elapsed = time.perf_counter() - begin
            model_before = controller.model.linear.tolist()
            pre_velocity = list(env.unwrapped.lander.linearVelocity)
            pre_tilt = float(env.unwrapped.lander.angle)
            original_power = LL.MAIN_ENGINE_POWER
            try:
                if tick >= change_step:
                    LL.MAIN_ENGINE_POWER = original_power * thrust_scale
                nxt, reward, term, trunc, _ = env.step(action)
            finally:
                LL.MAIN_ENGINE_POWER = original_power
            controller.observe(obs, action, nxt)
            if first_contact is None and np.any(nxt[6:]):
                first_contact = {"step": tick, "pre_contact_velocity": pre_velocity,
                                 "pre_contact_tilt": pre_tilt}
            records.append({"state": obs.tolist(), "action": action, "reward": float(reward),
                            "next_state": nxt.tolist(), "solve_ms": elapsed*1000,
                            "plan": controller.last_plan, "prediction": controller.last_prediction,
                            "plan_cost": controller.last_cost, "model_before": model_before,
                            "model": controller.model.linear.tolist(),
                            "angular_model": controller.model.angular.tolist(),
                            "prediction_error": controller.model.last_error})
            total += reward
            obs = nxt
        from lunar_mpc.environment import ground_line
        u = env.unwrapped
        return {"seed": seed, "return": total, "steps": len(records),
                **landing_result(env, term, trunc, obs), "first_contact": first_contact,
                "final_state": obs.tolist(), "records": records, "start": info["start"],
                "terrain": ground_line(env),
                "helipad": [u.helipad_x1, u.helipad_x2, u.helipad_y]}
    finally:
        env.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episodes", type=int, default=8)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--fixed-model", action="store_true")
    p.add_argument("--horizon", type=int, default=16)
    p.add_argument("--hold", type=int, default=4)
    p.add_argument("--beam", type=int, default=32)
    p.add_argument("--thrust-scale", type=float, default=1.)
    p.add_argument("--change-step", type=int, default=100)
    p.add_argument("--out", type=Path, default=Path("dist/mpc/evaluation.json"))
    p.add_argument("--replay", type=Path, help="write a self-contained interactive HTML replay")
    args = p.parse_args()
    if args.episodes < 1:
        p.error("episodes must be positive")
    if not 0 < args.thrust_scale <= 1 or args.change_step < 0:
        p.error("thrust-scale must be in (0, 1] and change-step nonnegative")
    cfg = MPCConfig(args.horizon, args.hold, args.beam, not args.fixed_model)
    episodes = []
    for seed in range(args.seed, args.seed+args.episodes):
        ep = run_episode(seed, cfg, args.thrust_scale, args.change_step)
        episodes.append(ep)
        print(f"seed={seed} return={ep['return']:.1f} steps={ep['steps']} "
              f"landed={ep['landed']} pad_margin={ep['pad_margin']:.3f}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    latencies = [r["solve_ms"] for ep in episodes for r in ep["records"]]
    data = {"config": vars(cfg), "thrust_scale": args.thrust_scale,
            "change_step": args.change_step, "episodes": episodes,
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "summary": {"episodes": len(episodes), "passed": sum(e["passed"] for e in episodes),
                        "landings": sum(e["landed"] for e in episodes),
                        "mean_return": float(np.mean([e["return"] for e in episodes])),
                        "worst_return": min(e["return"] for e in episodes),
                        "minimum_pad_margin": min(e["pad_margin"] for e in episodes),
                        "solve_ms_p50": float(np.percentile(latencies, 50)),
                        "solve_ms_p95": float(np.percentile(latencies, 95)),
                        "solve_ms_p99": float(np.percentile(latencies, 99)),
                        "solve_ms_max": max(latencies)}}
    payload = json.dumps(data, separators=(",", ":"))
    args.out.write_text(payload)
    if args.replay:
        template = Path(__file__).with_name("mpc_replay.html").read_text()
        args.replay.parent.mkdir(parents=True, exist_ok=True)
        args.replay.write_text(template.replace("__MPC_DATA__", payload.replace("<", "\\u003c")))
        print(f"Replay: {args.replay} (open the file directly)", flush=True)
    print(f"Saved {args.out}; passed {sum(e['passed'] for e in episodes)}/{len(episodes)}", flush=True)


if __name__ == "__main__":
    main()
