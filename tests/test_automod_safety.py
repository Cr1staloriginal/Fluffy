import unittest

from cogs.automod import is_ignored_channel, spam_bucket_key


class AutoModSafetyTests(unittest.TestCase):
    def test_known_ignored_channel_ids_are_ignored(self):
        self.assertTrue(is_ignored_channel(1473318583089234022, "general"))

    def test_unconfigured_channel_names_are_not_ignored(self):
        self.assertFalse(is_ignored_channel(123456789, "general"))

    def test_spam_tracking_is_scoped_to_guild_and_user(self):
        self.assertEqual(spam_bucket_key(10, 20), (10, 20))
        self.assertNotEqual(spam_bucket_key(10, 20), spam_bucket_key(11, 20))


if __name__ == "__main__":
    unittest.main()
