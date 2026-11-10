import unittest

from utils.ticket_metadata import build_ticket_topic, parse_ticket_topic


class TicketMetadataTests(unittest.TestCase):
    def test_round_trip(self):
        topic = build_ticket_topic(123456, "Техническая проблема", 789012)
        self.assertEqual(
            parse_ticket_topic(topic),
            {
                "creator": "123456",
                "category": "Техническая проблема",
                "claimed_by": "789012",
            },
        )

    def test_unclaimed_ticket_round_trip(self):
        metadata = parse_ticket_topic(build_ticket_topic(123456, "Общий вопрос"))
        self.assertEqual(metadata["creator"], "123456")
        self.assertEqual(metadata["claimed_by"], "")

    def test_unrelated_or_invalid_topics_are_ignored(self):
        self.assertEqual(parse_ticket_topic(None), {})
        self.assertEqual(parse_ticket_topic("ordinary channel"), {})
        self.assertEqual(parse_ticket_topic("fluffy_ticket|creator=not-an-id"), {})

    def test_topic_values_are_sanitized(self):
        topic = build_ticket_topic(123, "General|Injected\nValue", "not-an-id")
        metadata = parse_ticket_topic(topic)
        self.assertEqual(metadata["category"], "General Injected Value")
        self.assertEqual(metadata["claimed_by"], "")


if __name__ == "__main__":
    unittest.main()
