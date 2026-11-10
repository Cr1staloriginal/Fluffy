import unittest
from datetime import datetime, timedelta

from cogs.verification import is_submission_cooldown_active


class VerificationCooldownTests(unittest.TestCase):
    def test_recent_pending_submission_is_limited(self):
        now = datetime(2026, 11, 11, 12, 0, 30)
        submitted = now - timedelta(seconds=30)
        self.assertTrue(is_submission_cooldown_active(submitted, now, 60))

    def test_old_submission_is_not_limited(self):
        now = datetime(2026, 11, 11, 12, 0, 0)
        submitted = now - timedelta(seconds=90)
        self.assertFalse(is_submission_cooldown_active(submitted, now, 60))

    def test_malformed_timestamp_fails_open(self):
        self.assertFalse(is_submission_cooldown_active("not-a-timestamp"))

    def test_zero_cooldown_disables_limit(self):
        self.assertFalse(is_submission_cooldown_active("2026-11-11 12:00:00", cooldown_seconds=0))


if __name__ == "__main__":
    unittest.main()
