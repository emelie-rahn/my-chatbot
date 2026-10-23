## Section 6: Robustness and Red-Teaming

Instructions: 
Write at least 8 adversarial inputs, run them, and record what happened in a table: input, expected behavior, actual behavior, pass or fail. 

Include at least: a prompt injection ("ignore your instructions…"), an off-catalog request ("seats for a movie you don't show"), a mid-task topic switch ("wait, what are your hours?" while the bot is waiting for a slot), a negation, a very long message, and two slots in conflict ("Tuesday… no, Wednesday").
 
For each failure, explain why it happened, citing a specific line of code or prompt, and either fix it or explain what fixing it would take.

### 1. Prompt Rejection

- Result: Pass
- Reason: The bot doesn't reveal its instructions and falls back with a help message.
- Response: "Sorry, I didn't understand that. Type help to see what I can do. If you need a staff member, say talk to a human."

### 2. Unsupported Movie Tickets

- Result: Pass
- Reason: The bot explains it doesn't help with that task and falls back with a help message.
- Response: "Sorry, I didn't understand that. Type help to see what I can do. If you need a staff member, say talk to a human."

### 3. Switch to Asking About Hours Mid-Booking

- Result: Fail
- Reason: The bot fails because it repeats the date instead of recognizing the new request.
- Response: "What date would you like to attend? You can say tomorrow or a weekday."

This failure happened because it can't recognize a new intent. When a booking is currently in progress, the message handler processes the user's response as part of the current task.

 To fix this: 
- I would update `on_message` in the `src` folder to recognize new intents before processing a missing booking slot.
- If the recognizer identifies a supported question, the bot should be able to handle it without deleting the current task's information.
- Instead of repeating the prompt, the bot should be able to explain the limitation.

### 4. Negated Booking Request

- Result: Fail
- Reason: The bot continues with the booking, even though the user has indicated they don't want to.
- Response: "What time would you prefer?"

This failure happens because the bot can't catch the phrase "don't want to." It treats the phrase as requesting a booking for a class.

 To fix this: 
- I would want to add a negation check before starting a booking.

### 5. Very Long Repeated Message

- Result: Pass
- Reason: The bot doesn't crash or create an incorrect booking.
- Response: 

 "Please confirm this cancellation:

 - Class: Yoga
 - Date: 2026-10-30

 Reply yes to confirm the cancellation or no to keep it."

### 6. Correct Tuesday to Wednesday

- Result: Fail
- Reason: The bot only uses the first time given.
- Response: 

 "Please confirm your class booking:

 - Class: Yoga
 - Date: 2026-10-27
 - Time: 6 pm

 Reply yes to confirm or no to cancel. You can also correct a detail before confirming."

The bot failed because it can't handle a correction. I think both days are being picked up, but the bot only handles the first and can't update the second day to the current one.

 To fix this: 
- I would update date extraction to recognize correction phrases.
- I would want the bot to keep the most recent day stated in the prompt and make a correction while being able to preserve the class type and time.

### 7. Reply "Spin" When Asked for a Class Type

- Result: Pass
- Reason: When asked for a class type, the bot continues with the booking.
- Response: "What date would you like to attend? You can say tomorrow or a weekday."

### 8. Unsupported Class Type

- Result: Pass
- Reason: The bot rejects the unsupported class and suggests what the user can book.
- Response: "Spin is offered at 7 am, 5:30 pm in the demo catalog. What time would you prefer?"

### 9. Cancel, Then Say Not to Cancel

- Result: Fail
- Reason: The bot only takes in the first phrase, asking for the cancellation and doesn't recognize the second phrase.
- Response: 

 "Please confirm this cancellation:

 - Class: Yoga
 - Date: 2026-10-30

 Reply yes to confirm the cancellation or no to keep it."

This failure happens, like the others, because it hasn't been programmed to handle changes the user wants to make.

 To fix this: 
- Before the bot confirms with the user that they want to cancel a booking, it can check for a negation and correctly handle it.
- If the latest message indicates the user wants to withdraw from their current cancellation, the bot should be able to interpret that as a refusal.

### 10. Reply "Tomorrow" When Asked for a Time

- Result: Pass
- Reason: The bot asks for the time when prompted "tomorrow."
- Response: "What time would you prefer?"