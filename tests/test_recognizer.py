# Run with: python -m unittest
import unittest
from datetime import date

from src.recognizer import recognize

# A Monday, so weekday resolution is predictable.
TODAY = date(2026, 9, 28)


class IntentTests(unittest.TestCase):
    def assertIntent(self, text, intent):
        self.assertEqual(recognize(text, TODAY).intent, intent, text)

    def test_intents(self):
        self.assertIntent("hello", "Greeting")
        self.assertIntent("good evening", "Greeting")
        self.assertIntent("what can you do?", "Help")

        self.assertIntent("book a yoga class", "BookClass")
        self.assertIntent("book yoga tomorrow at 6 pm", "BookClass")
        self.assertIntent("sign me up for spinning", "BookClass")

        self.assertIntent("cancel my yoga booking", "CancelBooking")
        self.assertIntent("cancel my class reservation", "CancelBooking")

        self.assertIntent("show me the class schedule", "CheckSchedule")
        self.assertIntent("check my class booking", "CheckSchedule")

        self.assertIntent("find a Pilates class", "FindClass")
        self.assertIntent("are there any HIIT classes", "FindClass")

        self.assertIntent("never mind", "Cancel")

    def test_unknown_text_is_none(self):
        self.assertIntent("tell me a joke", "None")

    def test_entities_alone_have_no_intent(self):
        self.assertIntent("Yoga", "None")
        self.assertIntent("tomorrow", "None")
        self.assertIntent("6 pm", "None")

    def test_each_task_intent_has_at_least_eight_examples(self):
        from src.recognizer import INTENTS

        for intent in (
            "BookClass",
            "CancelBooking",
            "CheckSchedule",
            "FindClass",
        ):
            with self.subTest(intent=intent):
                self.assertGreaterEqual(len(INTENTS[intent]), 8)


class EntityTests(unittest.TestCase):
    def test_class_type_and_synonyms(self):
        result = recognize("book a yoga class", TODAY)
        self.assertEqual(result.get("class_type"), "Yoga")

        result = recognize("sign me up for spinning", TODAY)
        self.assertEqual(result.get("class_type"), "Spin")

        result = recognize("find Pilates", TODAY)
        self.assertEqual(result.get("class_type"), "Pilates")

    def test_dates_are_resolved(self):
        self.assertEqual(
            recognize("tomorrow", TODAY).get("date"),
            "2026-09-29",
        )
        self.assertEqual(
            recognize("friday", TODAY).get("date"),
            "2026-10-02",
        )
        self.assertEqual(
            recognize("next friday", TODAY).get("date"),
            "2026-10-09",
        )

    def test_time_extraction(self):
        self.assertEqual(
            recognize("book yoga at 6 pm", TODAY).get("time"),
            "6 pm",
        )
        self.assertEqual(
            recognize("book Pilates at 6:30 pm", TODAY).get("time"),
            "6:30 pm",
        )

    def test_multiple_entities_in_one_message(self):
        result = recognize("Book yoga tomorrow at 6 pm", TODAY)

        self.assertEqual(result.get("class_type"), "Yoga")
        self.assertEqual(result.get("date"), "2026-09-29")
        self.assertEqual(result.get("time"), "6 pm")


if __name__ == "__main__":
    unittest.main()