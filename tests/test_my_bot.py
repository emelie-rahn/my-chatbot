"""Tests for the gym class booking chatbot.

Run from the project root with:
    python -m unittest tests.test_my_bot

These tests focus on the rule-based recognizer, so they do not need the bot server.
"""

import unittest
from datetime import date

from src.recognizer import INTENTS, extract_entities, recognize


class TestGymBotRecognizer(unittest.TestCase):
    def test_required_gym_intents_exist(self):
        required = {"BookClass", "CancelBooking", "CheckSchedule", "FindClass"}
        self.assertTrue(required.issubset(INTENTS.keys()))

    def test_each_task_intent_has_at_least_eight_examples(self):
        for intent in ("BookClass", "CancelBooking", "CheckSchedule", "FindClass"):
            with self.subTest(intent=intent):
                self.assertGreaterEqual(len(INTENTS[intent]), 8)

    def test_booking_intent_extracts_class_date_and_time(self):
        result = recognize(
            "Book yoga tomorrow at 6 pm",
            today=date(2026, 10, 22),
        )
        self.assertEqual(result.intent, "BookClass")
        self.assertEqual(result.get("class_type"), "Yoga")
        self.assertEqual(result.get("date"), "2026-10-23")
        self.assertEqual(result.get("time"), "6 pm")

    def test_class_type_synonym_resolves_to_canonical_value(self):
        entities = extract_entities("Sign me up for spinning")
        class_entity = next(
            entity for entity in entities if entity.category == "class_type"
        )
        self.assertEqual(class_entity.value, "Spin")

    def test_cancel_booking_intent(self):
        result = recognize("Cancel my yoga booking")
        self.assertEqual(result.intent, "CancelBooking")
        self.assertEqual(result.get("class_type"), "Yoga")

    def test_schedule_intent(self):
        result = recognize("Show me the class schedule")
        self.assertEqual(result.intent, "CheckSchedule")

    def test_find_class_intent(self):
        result = recognize("Find Pilates")
        self.assertEqual(result.intent, "FindClass")
        self.assertEqual(result.get("class_type"), "Pilates")

    def test_bare_entity_has_no_new_intent(self):
        # The agent should interpret a bare entity as a slot answer when a task is active.
        result = recognize("Yoga")
        self.assertEqual(result.intent, "None")
        self.assertEqual(result.get("class_type"), "Yoga")

    def test_training_data_has_four_gym_task_intents(self):
        self.assertTrue(
            {"BookClass", "CancelBooking", "CheckSchedule", "FindClass"}.issubset(
                INTENTS
            )
        )


if __name__ == "__main__":
    unittest.main()