import json
import re
import sys
import traceback
from datetime import date
from os import environ

from dotenv import load_dotenv
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.hosting.core import (
    AgentApplication,
    Authorization,
    TurnState,
    TurnContext,
    MemoryStorage,
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env

from .recognizer import RecognizerResult, recognize


load_dotenv()

if not environ.get("CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"):
    # Allow local anonymous testing in Agents Playground.
    environ.setdefault(
        "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__ANONYMOUS_ALLOWED",
        "true",
    )

agents_sdk_config = load_configuration_from_env(environ)

STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
AUTHORIZATION = Authorization(
    STORAGE, CONNECTION_MANAGER, **agents_sdk_config
)
AUTH_CONFIGURATION = (
    CONNECTION_MANAGER.get_default_connection_configuration()
)

AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
    **agents_sdk_config,
)


# Demo gym catalog
CLASS_CATALOG = {
    "Yoga": ["9 am", "6 pm"],
    "Spin": ["7 am", "5:30 pm"],
    "Pilates": ["10 am", "6:30 pm"],
    "Strength Training": ["8 am", "5 pm"],
    "HIIT": ["12 pm", "6 pm"],
    "Swimming": ["7 am", "4 pm"],
    "Zumba": ["11 am", "7 pm"],
    "Boxing": ["5 pm", "6 pm"],
    "Dance": ["6 pm"],
    "Cycling": ["7 am", "5:30 pm"],
}

HELP_TEXT = (
    "Welcome to the Gym Class Booking Bot! \n\n"
    "I can help you with these tasks:\n\n"
    "- **BookClass:** Book a class, e.g. "
    '"Book yoga tomorrow at 6 pm."\n'
    "- **CancelBooking:** Cancel a reservation, e.g. "
    '"Cancel my yoga booking."\n'
    "- **CheckSchedule:** Check available classes or your bookings.\n"
    '- **FindClass:** Find a class, e.g. "Find Pilates."\n'
    '- **Cancel:** Stop the current task, e.g. "Never mind."\n'
    "- **Help:** Show these instructions.\n\n"
    "I will ask for missing details and ask you to confirm before "
    "completing a booking or cancellation.\n\n"
    "Type **/debug** to toggle recognizer output, or ask for a "
    "human representative to request staff assistance."
)

# Required slots and the questions used to fill them.
BOOKING_SLOTS = {
    "class_type": "Which class would you like to book?",
    "date": "What date would you like to attend? You can say tomorrow or a weekday.",
    "time": "What time would you prefer?",
}

CANCELLATION_SLOTS = {
    "class_type": "Which class booking would you like to cancel?",
    "date": "What date is your class booking?",
}

BOOKING = "ConversationState.booking"
DEBUG = "ConversationState.debug"


# Shared helpers

def _normalize_time(value):
    """Normalize spacing and punctuation for comparing catalog times."""
    value = re.sub(r"\s+", " ", str(value).lower().strip())
    return value.replace(".", "")


def _get_slots(result: RecognizerResult) -> dict:
    """Extract any supported task slots from one recognizer result."""
    slots = {}

    for slot in ("class_type", "date", "time"):
        value = result.get(slot)
        if value is not None:
            slots[slot] = value

    return slots


def _merge_slots(task: dict, result: RecognizerResult):
    """
    Update only slots explicitly provided in this message.

    This permits corrections such as "Actually, Tuesday" or
    "Make that 7 pm" without erasing the other saved details.
    """
    for slot, value in _get_slots(result).items():
        task[slot] = value


def _missing_slots(task: dict, slot_questions: dict) -> list[str]:
    return [slot for slot in slot_questions if not task.get(slot)]


def _valid_class(class_type: str) -> bool:
    return class_type in CLASS_CATALOG


def _valid_date(value: str) -> bool:
    try:
        parsed = date.fromisoformat(value)
        return parsed >= date.today()
    except (TypeError, ValueError):
        return False


def _class_times(class_type: str) -> str:
    return ", ".join(CLASS_CATALOG[class_type])


async def _ask_for_missing_slot(
    context: TurnContext,
    state: TurnState,
    task: dict,
    questions: dict,
):
    missing = _missing_slots(task, questions)

    if missing:
        task["asking_for"] = missing[0]
        state.set_value(BOOKING, task)
        await context.send_activity(questions[missing[0]])
        return True

    return False


async def _show_confirmation(context: TurnContext, state: TurnState, task: dict):
    task["status"] = "awaiting_confirmation"
    task.pop("asking_for", None)
    state.set_value(BOOKING, task)

    if task["task_type"] == "booking":
        await context.send_activity(
            "Please confirm your class booking:\n\n"
            f"- **Class:** {task['class_type']}\n"
            f"- **Date:** {task['date']}\n"
            f"- **Time:** {task['time']}\n\n"
            "Reply **yes** to confirm or **no** to cancel. "
            "You can also correct a detail before confirming."
        )
    else:
        await context.send_activity(
            "Please confirm this cancellation:\n\n"
            f"- **Class:** {task['class_type']}\n"
            f"- **Date:** {task['date']}\n\n"
            "Reply **yes** to confirm the cancellation or **no** to keep it."
        )



# Conversation events and commands

@AGENT_APP.conversation_update("membersAdded")
async def on_members_added(context: TurnContext, _state: TurnState):
    for member in context.activity.members_added or []:
        if member.id != context.activity.recipient.id:
            await context.send_activity(
                f"Welcome to the Gym Class Booking Bot! 🏋️\n\n{HELP_TEXT}"
            )
    return True


@AGENT_APP.message("/help")
async def on_help_command(context: TurnContext, _state: TurnState):
    await context.send_activity(HELP_TEXT)


@AGENT_APP.message("/debug")
async def on_debug(context: TurnContext, state: TurnState):
    debug = not state.get_value(DEBUG, lambda: False)
    state.set_value(DEBUG, debug)
    await context.send_activity(
        f"Debug output is {'on' if debug else 'off'}."
    )


# Intent handlers

async def on_greeting(
    context: TurnContext,
    _state: TurnState,
    _result: RecognizerResult,
):
    name = (
        context.activity.from_property.name
        if context.activity.from_property
        else None
    )
    await context.send_activity(
        f"Hello{', ' + name if name else ''}! 👋 "
        "Would you like to book a gym class or check the schedule?"
    )


async def on_help(
    context: TurnContext,
    _state: TurnState,
    _result: RecognizerResult,
):
    await context.send_activity(HELP_TEXT)


async def on_book_class(
    context: TurnContext,
    state: TurnState,
    result: RecognizerResult,
):
    task = state.get_value(BOOKING, dict)

    # Start a new booking task when there is no task in progress.
    if not task:
        task = {"task_type": "booking"}

    # A new booking request replaces the previous task's purpose.
    task["task_type"] = "booking"
    task["status"] = "collecting"
    _merge_slots(task, result)

    # Validate class type against the catalog.
    if task.get("class_type") and not _valid_class(task["class_type"]):
        task.pop("class_type", None)
        state.set_value(BOOKING, task)
        await context.send_activity(
            "I couldn't find that class in the demo catalog. "
            "Available classes are: "
            + ", ".join(CLASS_CATALOG.keys())
            + ". Which would you like?"
        )
        return

    # Validate the date before asking for the next slot.
    if task.get("date") and not _valid_date(task["date"]):
        task.pop("date", None)
        state.set_value(BOOKING, task)
        await context.send_activity(
            "That date is invalid or in the past. "
            "Please give me a future date."
        )
        return

    # Ask for the first missing slot in the defined order.
    if await _ask_for_missing_slot(
        context, state, task, BOOKING_SLOTS
    ):
        return

    # Check whether the requested time is offered for this class.
    offered_times = CLASS_CATALOG[task["class_type"]]
    requested_time = _normalize_time(task["time"])
    normalized_offered = {
        _normalize_time(time): time for time in offered_times
    }

    if requested_time not in normalized_offered:
        await context.send_activity(
            f"{task['class_type']} is offered at "
            f"{', '.join(offered_times)} in the demo catalog. "
            "What time would you prefer?"
        )
        task.pop("time", None)
        task["asking_for"] = "time"
        state.set_value(BOOKING, task)
        return

    # Ask before completing the booking.
    task["time"] = normalized_offered[requested_time]
    await _show_confirmation(context, state, task)


async def on_cancel_booking(
    context: TurnContext,
    state: TurnState,
    result: RecognizerResult,
):
    task = state.get_value(BOOKING, dict)

    if not task or task.get("task_type") != "cancellation":
        task = {"task_type": "cancellation"}

    task["status"] = "collecting"
    _merge_slots(task, result)

    if task.get("class_type") and not _valid_class(task["class_type"]):
        task.pop("class_type", None)
        state.set_value(BOOKING, task)
        await context.send_activity(
            "I couldn't find that class in the demo catalog. "
            "Available classes are: "
            + ", ".join(CLASS_CATALOG.keys())
            + ". Which booking would you like to cancel?"
        )
        return

    if task.get("date") and not _valid_date(task["date"]):
        task.pop("date", None)
        state.set_value(BOOKING, task)
        await context.send_activity(
            "That date is invalid or in the past. "
            "Please give me the future date of your booking."
        )
        return

    if await _ask_for_missing_slot(
        context, state, task, CANCELLATION_SLOTS
    ):
        return

    # This is a simulated cancellation; there is no live booking database.
    await _show_confirmation(context, state, task)


async def on_check_schedule(
    context: TurnContext,
    _state: TurnState,
    result: RecognizerResult,
):
    class_type = result.get("class_type")

    if class_type:
        if not _valid_class(class_type):
            await context.send_activity(
                "That class isn't in the demo catalog. Available classes: "
                + ", ".join(CLASS_CATALOG.keys())
                + "."
            )
            return

        when = result.get("date")
        time_text = (
            f" on {when}" if when else ""
        )
        await context.send_activity(
            f"📅 {class_type} class times{time_text}: "
            f"{_class_times(class_type)}.\n\n"
            "These are sample schedule times, not live availability."
        )
        return

    await context.send_activity(
        "Here is the demo class schedule:\n\n"
        + "\n".join(
            f"- **{name}:** {', '.join(times)}"
            for name, times in CLASS_CATALOG.items()
        )
        + "\n\nThese are sample times, not live availability."
    )


async def on_find_class(
    context: TurnContext,
    _state: TurnState,
    result: RecognizerResult,
):
    class_type = result.get("class_type")
    when = result.get("date")
    requested_time = result.get("time")

    if class_type and not _valid_class(class_type):
        await context.send_activity(
            "That class isn't in the demo catalog. Available classes: "
            + ", ".join(CLASS_CATALOG.keys())
            + "."
        )
        return

    if class_type:
        times = CLASS_CATALOG[class_type]

        if requested_time:
            normalized = _normalize_time(requested_time)
            matching = [
                time for time in times
                if _normalize_time(time) == normalized
            ]
            if not matching:
                await context.send_activity(
                    f"{class_type} isn't listed at {requested_time}. "
                    f"Sample times are: {', '.join(times)}."
                )
                return

        date_text = f" on {when}" if when else ""
        time_text = f" at {requested_time}" if requested_time else ""
        await context.send_activity(
            f"🔎 {class_type} is listed{date_text}{time_text}. "
            f"Sample times: {', '.join(times)}.\n\n"
            "This demo doesn't check real-time class capacity."
        )
        return

    await context.send_activity(
        "Which type of class are you looking for? For example, "
        "Yoga, Spin, Pilates, HIIT, Swimming, or Zumba."
    )


async def on_cancel(
    context: TurnContext,
    state: TurnState,
    _result: RecognizerResult,
):
    # Cancel the active task at any point.
    state.delete_value(BOOKING)
    await context.send_activity(
        "OK, I've cleared the task in progress. What else can I help with?"
    )


async def on_none(
    context: TurnContext,
    _state: TurnState,
    _result: RecognizerResult,
):
    await context.send_activity(
        "Sorry, I didn't understand that. Type **help** to see what I can do. "
        "If you need a staff member, say **talk to a human**."
    )


async def on_handoff(context: TurnContext, state: TurnState):
    # Clear the active task so the user can start again after handoff.
    state.delete_value(BOOKING)
    await context.send_activity(
        "I can help with basic class bookings, but this request needs staff "
        "assistance. Please contact the gym's front desk or staff team. "
        "This demo bot cannot transfer you to a live representative."
    )


# Confirmation and multi-turn task handling

def _is_yes(text: str) -> bool:
    return text.strip().lower() in {
        "yes", "y", "yeah", "yep", "sure", "confirm", "confirm it",
        "book it", "go ahead", "do it",
    }


def _is_no(text: str) -> bool:
    return text.strip().lower() in {
        "no", "n", "nope", "don't", "do not", "don't confirm",
        "keep it", "leave it",
    }


async def _handle_confirmation(
    context: TurnContext,
    state: TurnState,
    task: dict,
    text: str,
    result: RecognizerResult,
):
    if _is_yes(text):
        if task["task_type"] == "booking":
            response = (
                "✅ Booking confirmed (simulated)!\n\n"
                f"- **Class:** {task['class_type']}\n"
                f"- **Date:** {task['date']}\n"
                f"- **Time:** {task['time']}\n\n"
                "This is a demo confirmation; no real reservation was created."
            )
        else:
            response = (
                "✅ Cancellation confirmed (simulated) for "
                f"{task['class_type']} on {task['date']}.\n\n"
                "This demo does not connect to a real booking system."
            )

        state.delete_value(BOOKING)
        await context.send_activity(response)
        return True

    if _is_no(text):
        state.delete_value(BOOKING)
        await context.send_activity(
            "No changes made. The pending task has been cleared. "
            "What would you like to do next?"
        )
        return True

    # If the user supplies a correction, update only the provided slot.
    supplied_slots = _get_slots(result)
    if supplied_slots:
        _merge_slots(task, result)
        task["status"] = "collecting"
        state.set_value(BOOKING, task)

        if task["task_type"] == "booking":
            await on_book_class(context, state, result)
        else:
            await on_cancel_booking(context, state, result)
        return True

    await context.send_activity(
        "Please reply **yes** to confirm or **no** to cancel. "
        "You can also correct the class, date, or time."
    )
    return True


# Intent routing

INTENT_HANDLERS = {
    "Greeting": on_greeting,
    "Help": on_help,
    "BookClass": on_book_class,
    "CancelBooking": on_cancel_booking,
    "CheckSchedule": on_check_schedule,
    "FindClass": on_find_class,
    "Cancel": on_cancel,
    "None": on_none,
}


@AGENT_APP.activity("message")
async def on_message(context: TurnContext, state: TurnState):
    text = context.activity.text or ""
    stripped_text = text.strip()
    lowered = stripped_text.lower()

    # Recognize first so debug output can explain the prediction.
    result = recognize(stripped_text)

    if state.get_value(DEBUG, lambda: False):
        await context.send_activity(
            f"```json\n{json.dumps(result.to_dict(), indent=2)}\n```"
        )

    # Defined cases requiring staff assistance.
    handoff_phrases = (
        "talk to a human",
        "talk to a person",
        "human agent",
        "speak to a person",
        "speak to staff",
        "representative",
        "real person",
        "contact the front desk",
        "staff member",
    )
    if any(phrase in lowered for phrase in handoff_phrases):
        await on_handoff(context, state)
        return

    # Global task cancellation has priority over every active task.
    if result.intent == "Cancel":
        await on_cancel(context, state, result)
        return

    task = state.get_value(BOOKING, dict)

    # If the user is confirming a pending task, process yes/no first.
    if task and task.get("status") == "awaiting_confirmation":
        handled = await _handle_confirmation(
            context, state, task, stripped_text, result
        )
        if handled:
            return

    # Continue collecting details when the user answers a slot question.
    # A bare "Yoga", "tomorrow", or "7 pm" may have no intent of its own.
    if task and task.get("status") == "collecting":
        if result.intent in ("None", "BookClass", "CancelBooking"):
            if result.intent == "CancelBooking":
                task["task_type"] = "cancellation"
            elif result.intent == "BookClass":
                task["task_type"] = "booking"

            if task["task_type"] == "booking":
                await on_book_class(context, state, result)
            else:
                await on_cancel_booking(context, state, result)
            return

    # Route a new request to the matching handler.
    handler = INTENT_HANDLERS.get(result.intent, on_none)
    await handler(context, state, result)


@AGENT_APP.error
async def on_error(context: TurnContext, error: Exception):
    # In production, consider logging this to Azure Application Insights.
    print(
        f"\n[on_turn_error] unhandled error: {error}",
        file=sys.stderr,
    )
    traceback.print_exc()
    await context.send_activity(
        "The bot encountered an error. Please try again or contact gym staff."
    )
