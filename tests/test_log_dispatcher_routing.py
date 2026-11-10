import unittest

from utils.log_dispatcher import LogDispatcher


class LogDispatcherRoutingTests(unittest.TestCase):
    def test_event_environment_key_is_normalized(self):
        self.assertEqual(
            LogDispatcher._event_env_name("members", "member_join"),
            "LOG_CH_MEMBERS_MEMBER_JOIN",
        )

    def test_event_environment_key_rejects_empty_or_punctuation_only(self):
        self.assertIsNone(LogDispatcher._event_env_name("members", ""))
        self.assertIsNone(LogDispatcher._event_env_name("members", " !!! "))

    def test_event_environment_key_normalizes_mixed_case(self):
        self.assertEqual(
            LogDispatcher._event_env_name("messages", "Message Delete"),
            "LOG_CH_MESSAGES_MESSAGE_DELETE",
        )


if __name__ == "__main__":
    unittest.main()
