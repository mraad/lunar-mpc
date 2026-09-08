"""Verify the extracted evaluator helpers in a real, independently installed env."""
import importlib.util
import unittest

import gymnasium as gym
import numpy as np

from lunar_mpc.environment import StartPose, ground_line


class EnvironmentTest(unittest.TestCase):
    def test_seeded_pose_and_terrain(self):
        env = StartPose(gym.make('LunarLander-v3'), 6, .5)
        try:
            first, info = env.reset(seed=7)
            terrain = ground_line(env)
            second, repeated = env.reset(seed=7)
            np.testing.assert_array_equal(first, second)
            self.assertEqual(info['start'], repeated['start'])
            self.assertEqual(terrain, ground_line(env))
            self.assertTrue(2.4 <= abs(info['start'][0]) <= 6)
            self.assertTrue(.2 <= abs(info['start'][1]) <= .5)
            self.assertTrue(np.isfinite(terrain).all())
            self.assertEqual(np.asarray(terrain).shape[1], 2)
            next_obs, *_ = env.step(0)
            self.assertTrue(np.isfinite(next_obs).all())
        finally:
            env.close()

    def test_no_rl_dependency_in_locked_environment(self):
        self.assertIsNone(importlib.util.find_spec('lunar_rl'))
        self.assertIsNone(importlib.util.find_spec('torch'))


if __name__ == '__main__':
    unittest.main()
