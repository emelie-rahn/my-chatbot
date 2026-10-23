"""
A small rule-based intent and entity recognizer for a gym class booking bot.

The recognizer:
1. Extracts gym class types, dates, and times from a message.
2. Resolves class-type synonyms and relative dates to canonical values.
3. Replaces entities with placeholders before classifying intent.
4. Returns an intent, confidence score, extracted entities, and intent scores.

The result structure is kept compatible with the existing agent pattern.
"""

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta


# Training data: intents and their example utterances.

INTENTS: dict[str, list[str]] = {
    "Greeting": [
        "hello",
        "hi",
        "hey there",
        "good morning",
        "good afternoon",
        "good evening",
        "hello there",
        "hey",
    ],
    "Help": [
        "help",
        "what can you do",
        "how does this work",
        "show me the commands",
        "how do i use this bot",
        "what can you help me with",
        "i need help",
        "show me how this works",
    ],
    "BookClass": [
        "book a class",
        "book a @class_type class",
        "i want to book @class_type",
        "sign me up for @class_type",
        "reserve a spot in @class_type",
        "register me for a class",
        "sign me up for a class",
        "i want to attend @class_type on @date",
        "book @class_type at @time on @date",
        "schedule a @class_type class",
        "can i join @class_type @date",
        "reserve a spot in @class_type",
    ],
    "CancelBooking": [
        "cancel my booking",
        "cancel my class reservation",
        "i want to cancel a class",
        "cancel my @class_type booking",
        "remove me from @class_type",
        "i cannot attend my class",
        "withdraw my class registration",
        "cancel my reservation for @date",
        "i need to cancel my gym class",
        "cancel my spot in @class_type",
        "remove my reservation",
        "i don't want my booking anymore.",
    ],
    "CheckSchedule": [
        "show me the class schedule",
        "what classes are available",
        "show the gym schedule",
        "what classes are available on @date",
        "when is my @class_type class",
        "check my class booking",
        "what classes do i have booked",
        "show my upcoming reservations",
        "what time is @class_type on @date",
        "list the available class times",
        "what times is @class_type offered",
        "show me the timetable"
    ],
    "FindClass": [
        "find a class",
        "find a @class_type class",
        "are there any @class_type classes",
        "look for @class_type",
        "search for a gym class",
        "find a class on @date",
        "find @class_type at @time",
        "what @class_type classes can i take",
        "show me @class_type classes on @date",
        "i am looking for a fitness class",
        "do you offer boxing",
        "are there any @class_type classes",
    ],
    "Cancel": [
        "cancel",
        "never mind",
        "stop",
        "forget it",
        "start over",
        "cancel this",
        "let me start again",
        "nevermind",
    ],
}


# Minimum score for an intent to be accepted.
# Tune this using validation utterances, not the held-out test set.
INTENT_THRESHOLD = 0.4


# Words that usually do not distinguish one intent from another.
STOPWORDS = {
    "a", "an", "the", "to", "from", "in", "for", "on", "of", "at",
    "me", "my", "i", "please", "is", "it", "be", "do", "can",
    "could", "would", "there", "are", "any", "what", "when",
    "want", "i'm", "am", "have", "the", "this", "that",
}


# Entity definitions

# List entity: canonical class type -> accepted synonyms.
# Longer synonyms are matched first to avoid partial matches.
CLASS_TYPES: dict[str, list[str]] = {
    "Yoga": ["yoga", "yoga class"],
    "Spin": ["spin", "spin class", "spinning", "indoor cycling"],
    "Pilates": ["pilates", "pilates class"],
    "Strength Training": [
        "strength training",
        "strength class",
        "weight training",
        "weights",
    ],
    "HIIT": ["hiit", "high intensity interval training", "interval training"],
    "Swimming": ["swimming", "swim class", "swim"],
    "Zumba": ["zumba", "zumba class"],
    "Boxing": ["boxing", "boxing class"],
    "Dance": ["dance", "dance class"],
    "Cycling": ["cycling", "cycling class"],
}

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Regex entity: relative dates, weekdays, or ISO-format dates.
DATE_PATTERN = re.compile(
    r"\b(today|tomorrow|tonight|"
    r"(?:next\s+)?(?:"
    + "|".join(WEEKDAYS)
    + r")|\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)

# Regex entity: specific times or broad time-of-day preferences.
# Examples: "6 pm", "6:30pm", "18:30", "morning", "afternoon".
TIME_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?)?"
    r"|"
    r"\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)"
    r"|"
    r"morning|afternoon|evening|noon|midnight"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class Entity:
    category: str  # class_type, date, or time
    text: str  # the words as the user typed them
    value: str  # resolved canonical value
    offset: int  # character position in the message
    placeholder: str = field(repr=False, default="")


@dataclass
class RecognizerResult:
    text: str
    intent: str
    score: float
    entities: list[Entity]
    intent_scores: dict[str, float]

    def get(self, *categories: str):
        """Return the first resolved entity value in the requested categories."""
        for category in categories:
            for entity in self.entities:
                if entity.category == category:
                    return entity.value
        return None

    def to_dict(self) -> dict:
        """Return a serializable result without internal placeholder fields."""
        result = asdict(self)
        for entity in result["entities"]:
            del entity["placeholder"]
        return result


# Date resolution

def _resolve_date(text: str, today: date) -> str:
    """Resolve relative date phrases to YYYY-MM-DD."""
    text = text.lower().strip()

    if text == "today":
        return today.isoformat()

    # Treat "tonight" as today; time-of-day is extracted separately if supplied.
    if text == "tonight":
        return today.isoformat()

    if text == "tomorrow":
        return (today + timedelta(days=1)).isoformat()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    # A weekday means its next occurrence.
    # "Next Tuesday" means the Tuesday after the next occurrence.
    weekday = WEEKDAYS.index(text.split()[-1])
    days_ahead = (weekday - today.weekday()) % 7 or 7

    if text.startswith("next"):
        days_ahead += 7

    return (today + timedelta(days=days_ahead)).isoformat()

# Entity extraction

def extract_entities(text: str, today: date | None = None) -> list[Entity]:
    today = today or date.today()
    lowered = text.lower()

    entities: list[Entity] = []
    taken: list[tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < used_end and end > used_start
                   for used_start, used_end in taken)

    # Match longer class-type synonyms before shorter synonyms.
    synonyms = sorted(
        (
            (synonym, class_type)
            for class_type, synonym_list in CLASS_TYPES.items()
            for synonym in synonym_list
        ),
        key=lambda pair: -len(pair[0]),
    )

    for synonym, class_type in synonyms:
        for match in re.finditer(rf"\b{re.escape(synonym)}\b", lowered):
            start, end = match.span()

            if overlaps(start, end):
                continue

            entities.append(
                Entity(
                    "class_type",
                    text[start:end],
                    class_type,
                    start,
                    "@class_type",
                )
            )
            taken.append((start, end))

    # Dates are resolved to ISO-format strings.
    for match in DATE_PATTERN.finditer(text):
        start, end = match.span()

        if overlaps(start, end):
            continue

        entities.append(
            Entity(
                "date",
                match.group(0),
                _resolve_date(match.group(0), today),
                start,
                "@date",
            )
        )
        taken.append((start, end))

    # Times preserve the user's preference as a normalized lowercase string.
    for match in TIME_PATTERN.finditer(text):
        start, end = match.span()

        if overlaps(start, end):
            continue

        time_value = re.sub(r"\s+", " ", match.group(0).lower()).strip()
        time_value = time_value.replace(".", "")

        entities.append(
            Entity(
                "time",
                match.group(0),
                time_value,
                start,
                "@time",
            )
        )
        taken.append((start, end))

    return sorted(entities, key=lambda entity: entity.offset)

# Intent classification

def _tokens(text: str) -> set[str]:
    """Tokenize text while retaining entity placeholders such as @date."""
    return {
        word
        for word in re.findall(r"@?[a-z']+", text.lower())
        if word not in STOPWORDS
    }


def _similarity(a: set[str], b: set[str]) -> float:
    """Dice coefficient: 1.0 for identical word sets, 0.0 for no overlap."""
    if not a or not b:
        return 0.0

    return 2 * len(a & b) / (len(a) + len(b))


def classify_intent(
    text: str,
    entities: list[Entity],
) -> tuple[str, float, dict[str, float]]:
    # Replace entities with placeholders, starting at the end so offsets remain valid.
    normalized = text

    for entity in sorted(entities, key=lambda entity: -entity.offset):
        normalized = (
            normalized[:entity.offset]
            + entity.placeholder
            + normalized[entity.offset + len(entity.text):]
        )

    tokens = _tokens(normalized)

    scores = {
        intent: round(
            max(
                _similarity(tokens, _tokens(example))
                for example in examples
            ),
            2,
        )
        for intent, examples in INTENTS.items()
    }

    # Entity-only messages (e.g., "Yoga" or "tomorrow") do not start a new task.
    if not any(not token.startswith("@") for token in tokens):
        return "None", 0.0, scores

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score < INTENT_THRESHOLD:
        return "None", best_score, scores

    return best_intent, best_score, scores

# Public recognition function

def recognize(text: str, today: date | None = None) -> RecognizerResult:
    """
    Recognize a message and return its predicted intent and extracted entities.

    Example:
        recognize("Book yoga on Tuesday at 6 pm")
    """
    entities = extract_entities(text, today)
    intent, score, scores = classify_intent(text, entities)

    return RecognizerResult(
        text=text,
        intent=intent,
        score=score,
        entities=entities,
        intent_scores=scores,
    )