import unittest

import cogs.automod as automod
from cogs.automod import (
    IGNORED_CHANNEL_IDS,
    _parse_id_set,
    is_ignored_channel,
    is_ignored_member,
)


class AutoModExclusionTests(unittest.TestCase):
    def test_parse_id_set_accepts_comma_and_semicolon_separators(self):
        self.assertEqual(_parse_id_set("123, 456;789"), {123, 456, 789})

    def test_parse_id_set_ignores_invalid_and_non_positive_values(self):
        self.assertEqual(_parse_id_set("abc,0,-1,42"), {42})

    def test_ignored_channel_keeps_existing_exclusions(self):
        self.assertTrue(is_ignored_channel(next(iter(IGNORED_CHANNEL_IDS)), "general"))

    def test_ignored_channel_matches_configured_ids(self):
        previous = set(automod.ENV_IGNORED_CHANNEL_IDS)
        try:
            automod.ENV_IGNORED_CHANNEL_IDS = {8001}
            self.assertTrue(is_ignored_channel(8001, "ordinary-channel"))
            self.assertFalse(is_ignored_channel(8002, "ordinary-channel"))
        finally:
            automod.ENV_IGNORED_CHANNEL_IDS = previous

    def test_ignored_member_matches_configured_role_ids(self):
        previous = set(automod.ENV_IGNORED_ROLE_IDS)
        try:
            automod.ENV_IGNORED_ROLE_IDS = {9001}
            self.assertTrue(is_ignored_member([100, 9001]))
            self.assertFalse(is_ignored_member([100, 200]))
        finally:
            automod.ENV_IGNORED_ROLE_IDS = previous


if __name__ == "__main__":
    unittest.main()
