"""Regression tests for server setting validation."""
import unittest

from cogs.server_settings import validate_value


class ServerSettingsValidationTests(unittest.TestCase):
    def test_channel_id_must_be_numeric(self):
        with self.assertRaises(ValueError):
            validate_value("welcome_channel_id", "not-an-id")

    def test_channel_id_accepts_zero_to_disable(self):
        self.assertEqual(validate_value("welcome_channel_id", "0"), "0")

    def test_auto_message_interval_bounds(self):
        self.assertEqual(validate_value("auto_message_interval", "5"), "5")
        self.assertEqual(validate_value("auto_message_interval", "1440"), "1440")
        with self.assertRaises(ValueError):
            validate_value("auto_message_interval", "4")
        with self.assertRaises(ValueError):
            validate_value("auto_message_interval", "1441")

    def test_timezone_offset_bounds(self):
        self.assertEqual(validate_value("timezone_offset", "-12"), "-12")
        self.assertEqual(validate_value("timezone_offset", "14"), "14")
        with self.assertRaises(ValueError):
            validate_value("timezone_offset", "15")

    def test_server_birthday_is_normalized_and_validated(self):
        self.assertEqual(validate_value("server_birthday", "3-9"), "03-09")
        with self.assertRaises(ValueError):
            validate_value("server_birthday", "31-02")

    def test_boolean_is_normalized(self):
        self.assertEqual(validate_value("auto_message_enabled", "ДА"), "true")
        self.assertEqual(validate_value("auto_message_enabled", "off"), "false")
        with self.assertRaises(ValueError):
            validate_value("auto_message_enabled", "sometimes")


if __name__ == "__main__":
    unittest.main()
