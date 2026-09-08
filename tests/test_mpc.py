"""Focused controller checks: uv run python -m unittest discover -s tests -v."""
from types import SimpleNamespace
import unittest

import numpy as np

from lunar_mpc.mpc import AdaptiveMPC, Dynamics, DT, MPCConfig, OBS_SCALE, landing_result, state_from_obs


def observation(state, contacts=(0, 0)):
    return np.r_[np.asarray(state) / OBS_SCALE, contacts]


class MPCTest(unittest.TestCase):
    def test_observation_units_and_validation(self):
        np.testing.assert_allclose(state_from_obs(np.ones(8)), OBS_SCALE)
        for bad in (np.zeros(7), np.full(8, np.nan), np.full(8, np.inf)):
            with self.assertRaises(ValueError):
                state_from_obs(bad)
        for kwargs in ({"hold": 0}, {"beam": -1}, {"horizon": 0}, {"forgetting": 1.1}):
            with self.assertRaises(ValueError):
                MPCConfig(**kwargs)

    def test_dynamics_action_direction_and_no_mutation(self):
        x = np.zeros((4, 6))
        nxt = Dynamics().predict(x, np.arange(4))
        np.testing.assert_array_equal(x, np.zeros_like(x))
        self.assertAlmostEqual(nxt[0, 3], -10*DT)
        self.assertGreater(nxt[2, 3], 0)
        self.assertLess(nxt[1, 2], 0)
        self.assertGreater(nxt[1, 5], 0)
        self.assertGreater(nxt[3, 2], 0)
        self.assertLess(nxt[3, 5], 0)

    def test_estimator_tracks_unannounced_thrust_loss(self):
        truth, estimated = Dynamics(), Dynamics()
        for tick in range(300):
            if tick == 150:
                truth.linear[0] = 12.6
            # Excite every engine and vary attitude; the estimator receives
            # only observations and actions, never the changed parameter.
            action = tick % 4
            x = np.array([0., 5., .1, -.2, .3*np.sin(tick), .05])
            nxt = truth.predict(x, action)
            estimated.observe(observation(x), action, observation(nxt))
        self.assertLess(abs(estimated.linear[0]-12.6), .5)
        self.assertEqual(estimated.updates, 300)
        self.assertTrue(np.isfinite(estimated.p).all())

    def test_contact_and_fixed_model_do_not_learn(self):
        model = Dynamics()
        x = observation([0, 5, 0, 0, 0, 0])
        after = x.copy()
        after[3] = .1
        initial = model.linear.copy()
        model.observe(x, 2, after, learn=False)
        np.testing.assert_array_equal(initial, model.linear)
        self.assertGreater(model.last_error, 0)
        after[6] = 1
        model.observe(x, 2, after)
        np.testing.assert_array_equal(initial, model.linear)
        self.assertEqual(model.updates, 0)

    def test_replanning_is_deterministic_and_records_a_future(self):
        cfg = MPCConfig(horizon=5, hold=3, beam=8)
        a, b = AdaptiveMPC(cfg), AdaptiveMPC(cfg)
        obs = observation([3, 6, 0, -1, .2, 0])
        action = a.act(obs)
        self.assertEqual(action, b.act(obs))
        self.assertIn(action, range(4))
        self.assertEqual(a.last_plan, b.last_plan)
        self.assertEqual(len(a.last_prediction), cfg.horizon+1)
        np.testing.assert_allclose(a.last_prediction[0], state_from_obs(obs))
        self.assertEqual(a.last_plan[0], action)
        obs[6] = 1
        self.assertEqual(a.act(obs), 0)

    def test_terminal_scoring_rejects_crashes_timeouts_and_off_pad(self):
        u = SimpleNamespace(lander=SimpleNamespace(position=SimpleNamespace(x=10), angle=0., awake=False),
                            legs=[SimpleNamespace(ground_contact=True)]*2,
                            game_over=False, helipad_x1=8, helipad_x2=12)
        env = SimpleNamespace(unwrapped=u)
        obs = np.zeros(8)
        self.assertTrue(landing_result(env, True, False, obs)["passed"])
        u.game_over = True
        self.assertFalse(landing_result(env, True, False, obs)["landed"])
        u.game_over = False
        self.assertFalse(landing_result(env, False, True, obs)["landed"])
        u.lander.position.x = 12
        result = landing_result(env, True, False, obs)
        self.assertTrue(result["landed"])
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
