import unittest

from cogs.logs import _value


class LogEmbedFieldTests(unittest.TestCase):
    def test_empty_values_are_replaced(self):
        self.assertEqual(_value(""), "*пусто*")
        self.assertEqual(_value(None), "*пусто*")

    def test_long_values_are_truncated_below_discord_field_limit(self):
        value = _value("x" * 5000)
        self.assertLessEqual(len(value), 1024)
        self.assertTrue(value.endswith("…"))

    def test_caller_cannot_raise_the_embed_field_limit(self):
        value = _value("x" * 5000, limit=5000)
        self.assertLessEqual(len(value), 1024)

    def test_short_values_are_preserved(self):
        self.assertEqual(_value("hello"), "hello")


if __name__ == "__main__":
    unittest.main()
