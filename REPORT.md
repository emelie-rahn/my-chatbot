**Design Summary**  
The goal of the chatbot is to reduce the number of phone calls the gym’s front desk receives about class bookings by allowing members to manage common related tasks. The general goal for this project is that the chatbot will correctly identify the intent and extract the required entities The chatbot helps existing gym members book classes, cancel bookings, check class schedules, and find classes that match their interests. It simulates reservations using a predefined class catalog and schedule. The chatbot does not create memberships, process payments, provide personalized medical or fitness advice, or guarantee real-time class availability. A human staff member takes over when a request involves membership creation, an unavailable or invalid class, repeated recognition failures, or a request the chatbot cannot handle. Medical or safety questions are directed to an appropriate staff member.

| Intents:  BookClass CancelBooking CheckSchedule FindClass Greeting Help Cancel None | Slots and Entities:  Class type Class date Class time Membership id Booking id Fitness level |
| :---- | :---- |

**Architecture**  
![](/Users/emelierahn/Desktop/emelie-rahn-chatbot-midterm/dialogue_flow.png)

**Evaluation Results**  
![](/Users/emelierahn/Desktop/emelie-rahn-chatbot-midterm/threshold_sweep.png)
The above figure is the result of the baseline validation using \`validation.csv\`. The file contained 25 utterances. The baseline recognizer achieved a 76% intent accuracy and a macro-F1 score of 75.7%. Slot micro-precision, slot micro-recall, and slot micro-F1 all performed the same, with a score of 92.9%. Out-of-scope recall was 100%, indicating that all validation utterances labeled as out of scope were correctly classified as None or fallback.

The main errors stemmed from distinguishing between gym tasks. Two cancellation requests were classified as checks for the schedule. A booking request was classified as the user asking to find a class. A request to find a class was classified as a request to book a class. A help request and a schedule inquiry were interpreted as out of scope. From these errors, I would want to strengthen intent examples and tune the intent threshold.

The first improvement implemented was strengthening the intent examples. However, this didn’t impact any of the metrics. They all remained the same, along with the expected and predicted labels. The second improvement was tuning the intent threshold. Based on the figure above, I decided to set the threshold to 0.4. This increased intent accuracy from 76% to 80% and the intent marco-F1 score from 75.7% to 82.4%. Additionally, the confusion matrix showed less intents being categorized incorrectly.

| Baseline Validation | Strengthening Intent Examples | Tuning Intent Threshold |
| :---- | :---- | :---- |
| Utterances: 25 Intent accuracy: 0.760 Intent macro-F1: 0.757 Slot micro-precision: 0.929 Slot micro-recall: 0.929 Slot micro-F1: 0.929 Out-of-scope recall: 1.000 Confusion matrix (rows \= expected, columns \= predicted) Labels: \['BookClass', 'CancelBooking', 'CheckSchedule', 'FindClass', 'Greeting', 'Help', 'None'\] \[\[4 0 0 1 0 0 0\]  \[0 3 2 0 0 0 0\]  \[0 0 3 0 0 0 1\]  \[1 0 0 3 0 0 0\]  \[0 0 0 0 3 0 0\]  \[0 0 0 0 0 1 1\]  \[0 0 0 0 0 0 2\]\] | Utterances: 25 Intent accuracy: 0.760 Intent macro-F1: 0.757 Slot micro-precision: 0.929 Slot micro-recall: 0.929 Slot micro-F1: 0.929 Out-of-scope recall: 1.000 Confusion matrix (rows \= expected, columns \= predicted) Labels: \['BookClass', 'CancelBooking', 'CheckSchedule', 'FindClass', 'Greeting', 'Help', 'None'\] \[\[4 0 0 1 0 0 0\]  \[0 3 2 0 0 0 0\]  \[0 0 3 0 0 0 1\]  \[1 0 0 3 0 0 0\]  \[0 0 0 0 3 0 0\]  \[0 0 0 0 0 1 1\]  \[0 0 0 0 0 0 2\]\] | Utterances: 25 Intent accuracy: 0.800 Intent macro-F1: 0.824 Slot micro-precision: 0.929 Slot micro-recall: 0.929 Slot micro-F1: 0.929 Out-of-scope recall: 1.000 Confusion matrix (rows \= expected, columns \= predicted) Labels: \['BookClass', 'CancelBooking', 'CheckSchedule', 'FindClass', 'Greeting', 'Help', 'None'\] \[\[4 0 0 1 0 0 0\]  \[0 3 2 0 0 0 0\]  \[0 0 3 0 0 0 1\]  \[1 0 0 3 0 0 0\]  \[0 0 0 0 3 0 0\]  \[0 0 0 0 0 2 0\]  \[0 0 0 0 0 0 2\]\] |

**Error Analysis**  
The test set written contained 36 utterances. Intent accuracy and intent marco-F1 remains roughly the same across \`validation.csv\` and \`test.csv\`. One of the first things I notice is that out of scope recall drops from 100% to 88.9%. This means that eight out of the nine utterances in the None category were categorized correctly. 

The biggest issue is with the slot metrics. I think this could be due to how the bot handles categorizing. I probably didn’t add enough variation in the slots, causing the scores to drop. The bot should be able to interpret different ways to say the same thing. Such as, “11”, “11am”, “11 am”, “11:00”, or “11 o’clock”.

Another issue is with the categorization of \`CancelBooking.\` From the validation results, I know the bot struggles with handling canceling a class when, in the same sentence, a request for a booking has been made. Booking and cancellation requests might overlap in \`[recognizer.py](http://recognizer.py)\`, so the bot doesn’t handle it well. Another explanation is that the test set might phrase requests differently than in the validation set.

| Utterances: 36 Intent accuracy: 0.806 Intent macro-F1: 0.806 Slot micro-precision: 0.046 Slot micro-recall: 0.043 Slot micro-F1: 0.045 Out-of-scope recall: 0.889 Confusion matrix (rows \= expected, columns \= predicted) Labels: \['BookClass', 'CancelBooking', 'None'\] \[\[15  0  0\]  \[ 6  6  0\]  \[ 1  0  8\]\] |
| :---- |

**The Other Track**  
Track A might handle paraphrases and typos because it isn’t using example utterances. It allows for a bit more flexibility in what the user prompts. From the results above, the chatbot doesn’t handle negation well. Track B relies on someone else anticipating another user’s prompts. When there are several ways to articulate the same thing, a more flexible approach is best, which Track A provides.

Track B’s design makes it easier to guarantee business rules. With a more inflexible approach, it’s easier to categorize and measure the accuracy. With Track A, your metrics might change depending on the run. Track B provides more consistent results.

The needs of both tracks differ. Track requires an OpenAI API key and costs money to run validation tests. Your cost would also increase with the size of your test sets. Track B can be run offline and at no cost to the user. Both options allow the models to run locally on the user’s computer, which helps with privacy. Track B tends to run more slowly than Track A because of the manual checks that need to be done.

A hybrid approach might use Track B to score the confidence of what the user means, but still use code to slot intents and confirmations and cancellations. The LLM would extract and return a JSON with intent, class type, date, and time. We can use Track B’s aspects of checking the written code against the JSON. I think this would also help with corrections and negations.

**Limitations and Next Steps**  
If given two more weeks, I would focus on improving the intent classification. The bot struggles with multiple requests in the same prompt. I would also like to expand on the current intents, I think they feel a bit limited. To allow for more flexibility with the bot, I might also expand the class schedule. 