import unittest

from cogs.antiraid import RAID_CONFIG


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


if __name__ == "__main__":
    unittest.main()
