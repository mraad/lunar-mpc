"""Evaluator-only starting-pose and terrain helpers.

Extracted and modified from lunar-rl on 2026-09-08 to remove RL dependencies.
Copyright 2026 mraad. Licensed under Apache-2.0; see LICENSE.
"""
import math

import gymnasium as gym
import numpy as np


class StartPose(gym.Wrapper):
    """Spawn the lander off the pad and tilted.

    Vanilla LunarLander always spawns dead centre above the helipad at angle 0;
    the only per-seed randomness is a small force impulse, so **no choice of seed
    varies the start pose**.  This rigidly transforms the lander and both legs
    after reset — rigid so the revolute joints stay satisfied — and then
    re-derives the observation exactly the way the env does, since
    `LunarLander.reset` itself ends with an idle step.

    Draws from the env's own RNG, so the pose is a deterministic function of the
    seed: seed N now genuinely means a different approach, not just different
    terrain.
    """

    def __init__(self, env: gym.Env, x_range: float = 0.0, tilt_range: float = 0.0):
        super().__init__(env)
        self.x_range, self.tilt_range = x_range, tilt_range
        self.start = (0.0, 0.0)

    def reset(self, *, seed=None, options=None):
        obs, info = self.env.reset(seed=seed, options=options)
        u = self.env.unwrapped
        # Magnitude floor at 40% of range: a plain uniform draw would sometimes
        # land back on the pad (half-width 2.0) at a tilt too small to see.
        def draw(rng: float) -> float:
            if not rng:
                return 0.0
            sign = 1.0 if u.np_random.random() < 0.5 else -1.0
            return sign * float(u.np_random.uniform(0.4 * rng, rng))

        dx, tilt = draw(self.x_range), draw(self.tilt_range)
        self.start = (dx, tilt)
        if dx or tilt:
            cx, cy = u.lander.position.x, u.lander.position.y
            c, s = math.cos(tilt), math.sin(tilt)
            for b in [u.lander, *u.legs]:
                px, py = b.position.x - cx, b.position.y - cy
                b.position = (cx + dx + c * px - s * py, cy + s * px + c * py)
                b.angle += tilt
            idle = np.array([0.0, 0.0], dtype=np.float32) if u.continuous else 0
            obs = u.step(idle)[0]
        info["start"] = self.start
        return obs, info


def ground_line(env: gym.Env) -> list[list[float]]:
    """Terrain top edge, recovered from the sky polygons the env builds on reset."""
    polys = env.unwrapped.sky_polys
    pts = [[round(float(p[0][0]), 2), round(float(p[0][1]), 2)] for p in polys]
    pts.append([round(float(polys[-1][1][0]), 2), round(float(polys[-1][1][1]), 2)])
    return pts
