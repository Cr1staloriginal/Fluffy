import unittest

from utils.guild_guard import is_allowed_guild


class GuildGuardTests(unittest.TestCase):
    def test_accepts_only_the_configured_guild(self):
        self.assertTrue(is_allowed_guild(123456789, 123456789))

    def test_rejects_a_different_guild(self):
        self.assertFalse(is_allowed_guild(987654321, 123456789))

    def test_rejects_missing_guild_context(self):
        self.assertFalse(is_allowed_guild(None, 123456789))

    def test_rejects_unconfigured_or_invalid_target(self):
        self.assertFalse(is_allowed_guild(123456789, 0))
        self.assertFalse(is_allowed_guild(None, 0))


if __name__ == "__main__":
    unittest.main()
