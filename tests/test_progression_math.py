import unittest

from utils.progression_math import (
    earned_achievement_keys,
    level_for_xp,
    total_xp_for_level,
    xp_progress,
)


class ProgressionMathTests(unittest.TestCase):
    def test_level_boundaries(self):
        self.assertEqual(level_for_xp(0), 0)
        self.assertEqual(level_for_xp(99), 0)
        self.assertEqual(level_for_xp(100), 1)
        self.assertEqual(level_for_xp(total_xp_for_level(2)), 2)

    def test_progress_is_relative_to_current_level(self):
        self.assertEqual(xp_progress(0), (0, 0, 100))
        self.assertEqual(xp_progress(125), (1, 25, 200))

    def test_negative_xp_is_rejected(self):
        with self.assertRaises(ValueError):
            level_for_xp(-1)

    def test_achievements_are_milestone_based(self):
        self.assertEqual(earned_achievement_keys(0, 0), set())
        self.assertIn("level_5", earned_achievement_keys(5, 20))
        self.assertIn("messages_100", earned_achievement_keys(0, 100))
        self.assertIn("messages_1000", earned_achievement_keys(25, 1000))


if __name__ == "__main__":
    unittest.main()
