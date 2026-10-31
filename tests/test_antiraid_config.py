import unittest

from cogs.antiraid import RAID_CONFIG, is_auto_punish_enabled


class AntiRaidConfigTests(unittest.TestCase):
    def test_five_channel_deletions_in_one_second_trigger_raid_threshold(self):
        config = RAID_CONFIG["удаление_каналов"]
        self.assertEqual(config["limit"], 5)
        self.assertEqual(config["time_window"], 1)
        self.assertEqual(config["punishment"], "clear_roles_kick")

    def test_other_channel_actions_keep_separate_thresholds(self):
        self.assertIn("создание_каналов", RAID_CONFIG)
        self.assertIn("изменение_каналов", RAID_CONFIG)
        self.assertNotEqual(
            RAID_CONFIG["удаление_каналов"]["time_window"],
            RAID_CONFIG["изменение_каналов"]["time_window"],
        )

    def test_automatic_punishment_is_disabled_by_default(self):
        self.assertFalse(is_auto_punish_enabled(None))

    def test_automatic_punishment_requires_explicit_opt_in(self):
        self.assertFalse(is_auto_punish_enabled("false"))
        self.assertFalse(is_auto_punish_enabled("0"))
        self.assertTrue(is_auto_punish_enabled("true"))
        self.assertTrue(is_auto_punish_enabled("1"))


if __name__ == "__main__":
    unittest.main()
