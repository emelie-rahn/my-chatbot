### Design Document

#### Domain: Gym class booking

#### Business Goal
Reduce the number of phone calls the gym’s front desk receives about class bookings by 80% by allowing members to manage common related tasks through the chatbot.
  
#### SMART Goal
On a test set of at least 40 previously unseen user utterances, the chatbot will correctly identify the intent and extract the required entities in at least 85% of cases. For valid booking requests, it will collect the required information and reach a confirmed booking in four or fewer bot turns for at least 90% of requests that can be completed successfully.
  
#### Scope
The chatbot helps existing gym members book classes, cancel bookings, check class schedules, and find classes that match their interests. It simulates reservations using a predefined class catalog and schedule. The chatbot does not create memberships, process payments, provide personalized medical or fitness advice, or guarantee real-time class availability. A human staff member takes over when a request involves membership creation, an unavailable or invalid class, repeated recognition failures, or a request the chatbot cannot handle. Medical or safety questions are directed to an appropriate staff member.

#### Intents

`book_class`
- I’d like to book a yoga class.
- Sign me up for a spin class on Friday.
- Can you reserve a spot in pilates tomorrow morning?
- I want to join the 6pm strength class.

`cancel_booking`
- Cancel my yoga reservation.
- I can’t make my spin class tomorrow.
- Please remove me from pilates on Friday.
- I’d like to give up my spot in the 6pm class.

`check_schedule`
- What classes are available tomorrow?
- Show me the yoga schedule for Friday.
- When is the next spin class?
- What time does Pilates start on Monday?

`find_class`
- Do you offer beginner yoga?
- Find me a strength class in the evening.
- What classes do you have on Saturday morning?
- I'm looking for a low-impact fitness class.

`greeting`
- Hi!
- Hello there.
- Good morning.
- Hey, are you available?

`help`
- What can you help me with?
- How does this chatbot work?
- What can I do here?
- Can you explain how to book a class?

`cancel`
- Never mind.
- Forget it.
- Stop what we're doing.
- I don't want to continue.

`none`
- What's the weather today?
- Can you recommend a restaurant?
- Tell me a joke.
- Can you create a new gym membership for me?

#### Slots and Entities

`class_type`
- Type: List and catalog
- Allowed values and synonyms:
  - Yoga, spin, pilates, strength, cycling
  - Cycling, bike class = spin
  - Weight training = strength
- Required? Yes, for booking and specific class schedules

`class_date`
- Type: Date entity
- Allowed values and synonyms:
  - Today, tomorrow, next [day of the week]
- Required? Yes, for booking and specific class schedules

`class_time`
- Type: List
- Allowed values and synonyms:
  - Morning (5am - 11:59am)
  - Afternoon (12pm - 4:59pm)
  - Evening (5pm - 9pm)
- Required? Yes, for booking when needing to identify a specific session

`membership_id`
- Type: Regex
- Allowed values and synonyms:
  - Ex: `^GYM-[0-9]{5}$`
- Required? Yes, for cancelation

`booking_id`
- Type: Regex
- Allowed values and synonyms:
  - Ex: `^BK-[0-9]{5}$`
  - Needs to match an existing booking
- Required? Needed to clarify who needs a cancellation

`fitness_level`
- Type: List
- Allowed values and synonyms:
  - Beginner, intermediate, advanced
  - New to exercise = beginner
  - Experienced = advanced
- Required? No, used to filter recommendations

#### Dialogue Flow
![image](/Users/emelierahn/Desktop/emelie-rahn-chatbot-midterm/dialogue_flow.png)
  
#### Track Choice
I chose Track B because its example-utterance recognizer, list entities, and regex entities provide a straightforward way to identify gym-related intents and extract structured booking information. The class catalog and conversation state will let me implement validation, slot filling, and confirmation explicitly. Testing the bot on unseen utterances will help me evaluate how well this approach generalizes and where it struggles compared with an LLM-based chatbot.