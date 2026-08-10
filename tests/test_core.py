import unittest

from aiogram.enums import MessageEntityType
from aiogram.types import MessageEntity

from main import extract_custom_emoji_ids, format_uptime, parse_admin_ids


class CoreTests(unittest.TestCase):
    def test_parse_admin_ids_accepts_commas_and_spaces(self) -> None:
        self.assertEqual(parse_admin_ids("123,456 789"), {123, 456, 789})

    def test_extract_custom_emoji_ids_keeps_order_and_removes_duplicates(self) -> None:
        entities = [
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=0,
                length=1,
                custom_emoji_id="111",
            ),
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=1,
                length=1,
                custom_emoji_id="222",
            ),
            MessageEntity(
                type=MessageEntityType.CUSTOM_EMOJI,
                offset=2,
                length=1,
                custom_emoji_id="111",
            ),
        ]

        self.assertEqual(extract_custom_emoji_ids(entities), ["111", "222"])

    def test_extract_custom_emoji_ids_ignores_other_entities(self) -> None:
        entities = [
            MessageEntity(type=MessageEntityType.BOLD, offset=0, length=4),
        ]

        self.assertEqual(extract_custom_emoji_ids(entities), [])

    def test_format_uptime(self) -> None:
        self.assertEqual(format_uptime(0), "0s")
        self.assertEqual(format_uptime(61), "1m 1s")
        self.assertEqual(format_uptime(90061), "1d 1h 1m 1s")


if __name__ == "__main__":
    unittest.main()
