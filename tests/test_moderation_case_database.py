import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aiosqlite

import database


class ModerationCaseDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "test.db"
        with patch.dict(os.environ, {"GUILD_ID": "12345"}):
            await database.init_db()

    async def asyncTearDown(self):
        database.DB_PATH = self.previous_path
        self.temp_dir.cleanup()

    async def test_case_round_trip_and_guild_isolation(self):
        case_id = await database.add_moderation_case(
            12345, 222, 333, "timeout", "Spam", "manual"
        )
        row = await database.get_moderation_case(12345, case_id)
        self.assertIsNotNone(row)
        self.assertEqual(row[2], 222)
        self.assertEqual(row[3], 333)
        self.assertEqual(row[4], "timeout")
        self.assertIsNone(await database.get_moderation_case(99999, case_id))

    async def test_get_warn_returns_details_before_removal(self):
        warn_id = await database.add_warn(777, 888, "Test reason", "automod", "https://discord.com/channels/1/2/3")
        warning = await database.get_warn(warn_id)
        self.assertIsNotNone(warning)
        self.assertEqual(warning[1], 777)
        self.assertEqual(warning[2], 888)
        self.assertEqual(warning[3], "Test reason")
        self.assertEqual(warning[5], "https://discord.com/channels/1/2/3")
        self.assertIsNone(await database.get_warn(999999))

    async def test_existing_warns_are_backfilled_once(self):
        async with aiosqlite.connect(str(database.DB_PATH)) as db:
            await db.execute(
                """INSERT INTO warns
                   (user_id, moderator_id, reason, rule_name, message_link, date)
                   VALUES (777, 0, 'Old warning', 'automod', '', '2026-01-01T00:00:00')"""
            )
            await db.commit()

        with patch.dict(os.environ, {"GUILD_ID": "12345"}):
            await database.init_db()
            await database.init_db()

        rows = await database.get_user_moderation_cases(12345, 777, 25)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "warn")
        self.assertEqual(rows[0][5], "Old warning")


if __name__ == "__main__":
    unittest.main()
