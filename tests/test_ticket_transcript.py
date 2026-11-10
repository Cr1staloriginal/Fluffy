import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from cogs.tickets import render_ticket_transcript


class TicketTranscriptTests(unittest.TestCase):
    def test_renders_author_content_and_attachments(self):
        author = SimpleNamespace(id=123, display_name="Tester")
        attachment = SimpleNamespace(filename="image.png", url="https://cdn.example/image.png")
        message = SimpleNamespace(
            author=author,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            content="Hello Fluffy",
            attachments=[attachment],
            embeds=[],
        )
        transcript = render_ticket_transcript([message])
        self.assertIn("Tester (ID: 123)", transcript)
        self.assertIn("Hello Fluffy", transcript)
        self.assertIn("image.png", transcript)
        self.assertIn("https://cdn.example/image.png", transcript)

    def test_empty_transcript_has_readable_fallback(self):
        self.assertEqual(render_ticket_transcript([]), "В тикете пока нет сообщений.")

    def test_transcript_respects_size_limit(self):
        author = SimpleNamespace(id=1, display_name="Tester")
        message = SimpleNamespace(author=author, created_at=None, content="x" * 100, attachments=[], embeds=[])
        transcript = render_ticket_transcript([message], max_chars=20)
        self.assertIn("сокращён", transcript)


if __name__ == "__main__":
    unittest.main()
