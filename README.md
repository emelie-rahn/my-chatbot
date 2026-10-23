## Gym Class Booking Bot

### Overview

The Gym Class Booking Bot is a chatbot designed to help users book gym classes and ask questions about the classes a gym offers. Instead of calling the front desk, users can interact with the chatbot to request bookings, cancel reservations, check schedules, and find classes.

Note: This is a demonstration chatbot. All bookings and cancellations are simulated and do not affect real gym reservations.

### Requirements

- Python 3.10 or newer
- Node.js and npm

### Installation and Setup

Run the following commands from the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

On Windows, activate the virtual environment using:

```powershell
.venv\Scripts\activate
```

When the server starts successfully, you should see a message similar to:

```text
======== Running on http://localhost:3978 ========
```

Keep this terminal window open while using the bot.

### Launching the Chat Playground

Open a second terminal window and navigate to the project directory. Install and launch the Microsoft Agents Playground tool:

```bash
npm install -g @microsoft/teams-app-test-tool
teamsapptester
```

The Playground will open a chat in your browser connected to the locally running bot at `http://localhost:3978/api/messages`.

### Features and Supported Intents

The chatbot supports the following intents:

- BookClass: Book a gym class by providing the class type, date, and time.
- CancelBooking: Request cancellation of a reservation.
- CheckSchedule: Ask about class schedules or availability.
- FindClass: Find information about a particular class.
- Cancel: Stop the current task.
- Help: Display instructions and examples.

The bot asks follow-up questions when required information is missing and requests confirmation before completing a booking or cancellation.

### Example Usage

A user can start a booking with a request such as:

```text
User: Book yoga tomorrow at 6 pm.
Bot: Please confirm your class booking:
     - Class: Yoga
     - Date: [resolved date]
     - Time: 6 pm
     Reply yes to confirm or no to cancel.
```

If the user leaves out a required detail, the bot will ask for the missing information before presenting the confirmation.

### Testing

Run the unit tests from the project directory with the virtual environment activated:

```bash
python -m unittest
```

These tests check the behavior covered by the project's test suite.

If using the separate intent-recognition evaluation scripts, run the validation or test evaluation commands documented in the `eval/` directory.

### Limitations

- All bookings and cancellations are simulated.
- Class schedules and availability use demonstration data.
- The chatbot does not connect to a live gym booking system.
- The bot can misunderstand ambiguous requests, corrections, or negated instructions.