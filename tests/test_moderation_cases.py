import unittest

from cogs.moderation_cases import _case_line


class ModerationCaseFormattingTests(unittest.TestCase):
    def test_formats_system_warning_without_fake_moderator(self):
        row = (7, 1, 2, 0, "warn", "Repeated links", "automod", "", "2026-11-11 10:00:00")
        rendered = _case_line(row)
        self.assertIn("Автомод / система", rendered)
        self.assertIn("Repeated links", rendered)
        self.assertIn("#7", rendered)

    def test_formats_known_action_and_sanitizes_newlines(self):
        row = (8, 1, 2, 3, "ban", "First line\nSecond line", "manual", "", "2026-11-11")
        rendered = _case_line(row)
        self.assertIn("Блокировка", rendered)
        self.assertIn("<@3>", rendered)
        self.assertNotIn("\nSecond line", rendered)


if __name__ == "__main__":
    unittest.main()
