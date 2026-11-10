import copy
import unittest

from cogs.antiraid import build_backup_document, validate_backup_document


class BackupIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "id_сервера": 12345,
            "категории": [{"название": "Общее"}],
            "каналы": [{"тип": "текстовый", "название": "чат"}],
            "роли": [{"название": "Участник"}],
        }

    def test_versioned_backup_round_trip(self):
        document = build_backup_document(self.snapshot)
        self.assertTrue(validate_backup_document(document, 12345)[0])

    def test_tampered_backup_is_rejected(self):
        document = build_backup_document(self.snapshot)
        document["каналы"][0]["название"] = "изменено"
        valid, reason = validate_backup_document(document, 12345)
        self.assertFalse(valid)
        self.assertIn("контрольная сумма", reason)

    def test_wrong_guild_is_rejected(self):
        document = build_backup_document(self.snapshot)
        self.assertFalse(validate_backup_document(document, 999)[0])

    def test_legacy_backup_remains_supported(self):
        legacy = copy.deepcopy(self.snapshot)
        valid, reason = validate_backup_document(legacy, 12345)
        self.assertTrue(valid)
        self.assertEqual(reason, "legacy")

    def test_explicit_old_version_is_not_treated_as_legacy(self):
        legacy = copy.deepcopy(self.snapshot)
        legacy["format_version"] = 1
        self.assertFalse(validate_backup_document(legacy, 12345)[0])

    def test_version_downgrade_cannot_bypass_checksum(self):
        document = build_backup_document(self.snapshot)
        document["format_version"] = 1
        document.pop("integrity")
        self.assertFalse(validate_backup_document(document, 12345)[0])

    def test_invalid_structure_is_rejected(self):
        invalid = {"id_сервера": 12345, "категории": [], "каналы": []}
        self.assertFalse(validate_backup_document(invalid, 12345)[0])


if __name__ == "__main__":
    unittest.main()
