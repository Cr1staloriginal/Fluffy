import unittest

from cogs.temporary_voice import normalize_room_name, parse_member_id, parse_user_limit


class TemporaryVoiceInputTests(unittest.TestCase):
    def test_parse_member_id_accepts_id_and_mentions(self):
        self.assertEqual(parse_member_id("123456789012345678"), 123456789012345678)
        self.assertEqual(parse_member_id("<@123456789012345678>"), 123456789012345678)
        self.assertEqual(parse_member_id("<@!123456789012345678>"), 123456789012345678)

    def test_parse_member_id_rejects_invalid_values(self):
        self.assertIsNone(parse_member_id("not-a-user"))
        self.assertIsNone(parse_member_id("123 abc"))

    def test_user_limit_range(self):
        self.assertEqual(parse_user_limit("0"), 0)
        self.assertEqual(parse_user_limit("99"), 99)
        self.assertIsNone(parse_user_limit("-1"))
        self.assertIsNone(parse_user_limit("100"))
        self.assertIsNone(parse_user_limit("many"))

    def test_room_name_is_trimmed_and_limited(self):
        self.assertEqual(normalize_room_name("  cozy   room  "), "cozy room")
        self.assertEqual(len(normalize_room_name("x" * 150)), 100)
        self.assertEqual(normalize_room_name("   "), "")


if __name__ == "__main__":
    unittest.main()
