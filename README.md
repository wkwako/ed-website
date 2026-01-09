# Improving Students’ Code Comprehension Ability Through LLM-Generated Practice Problems

<span style="font-size: 11px;">*Please see "Improving Students’ Code Comprehension Ability Through LLM-Generated Practice Problems.pdf" in the files for a more formal write up.</span>


## Introduction

I developed a web application that aims to improve students’ code reading abilities by generating practice problems for students to solve. Rather than asking students to write code themselves, my project creates problems that rely on a student’s code comprehension ability. The webapp was created with HTML, CSS, Javascript, and Python, and models by OpenAI and Anthropic are used to generate problems of varying types. An options panel gives users agency over several aspects of problem generation including syntax, topic, and problem length. API calls are made to OpenAI’s GPT 4.1-mini model and Anthropic’s Claude 3.5 Haiku model for problem generation. Before code is shown to users, I verify that it is safe to run, and use the ast python package to confirm it contains user-selected structures. Specifically, OpenAI’s model is used for initial problem generation, and Anthropic’s model is used to regenerate the problem should it fail to meet user specifications.

#### Focus on introductory CS students

I focus on a system geared specifically towards introductory CS students. The gap between teaching materials for writing code versus reading and tracing through code starts early. Starting computer science with a stronger foundation will contribute to future aptitude. 

### System Architecture and Data Flow

The frontend uses HTML, CSS, and Javascript to display and catch user actions, while the backend uses Django and Python. The following outlines the data flow of the website:

1. The user navigates to /practice/, which renders the default practice.html page. On the backend, Django connects the url (/practice/) in urls.py to the view (practice()) in views.py. The practice() function contains the logic for rendering the page, sending info back to the frontend to display it to the user. 
2. The user clicks the Generate button. The frontend gathers relevant information like difficulty level, problem length, and subject, and sends it to the backend.
3. The backend randomly selects a problem type to generate: "determine the output", "docstring writing", or "rearrange the code."
4. The backend creates the query for the LLM. The user's specifications are converted to strings, concatenated, and formed into a list of "dos" and "donts" for the LLM. In addition, instructions are added to the query specific to the problem type.
5. The query is sent to ChatGPT, which generates a block of code formatted as a string.
6. When we receieve a response, we perform a validation step. This includes verifying that the code runs without errors, and confirming that it contains the user-defined specifications.
7. At this point, we store information about the problem, such as the problem type, difficulty, generated structures, and the answer.
8. The code is sent back to the frontend, and is displayed to the user.

Lastly, depending on the problem type, the user has different ways of submitting an answer. User-submitted answers follow a similar pattern to the above: they are sent to the backend, compared against the ground truth answer, then sent back to the frontend and to the user for review.

### Failure modes and Guardrails

There are several points at which the previously enumerated data flow may fail. These include:
1. The response from the backend may be in the wrong format (not POST). This is resolved by immediately sending another request to the backend.
2. We response from ChatGPT fails, either due to an error message, or a timeout. This is resolved by immediately sending another request to ChatGPT.
3. During the code validation step, we may discover that the code has an error. In this case, we capture the error message, and send the code and its error message to Anthropic to be fixed.
4. During the code validation step, we may discover that the code fails to meet user specifications. In this case, we send the code along with its faults back to ChatGPT and ask for it to be fixed. If the code fails for a second time to meet user specifications, we try a last time, but use a more robust model.

### Evaluation and Iteration Strategy
There are several ways in which we evaluate the model and iterate on its failures. Many of which involve asking questions about the generated code:
1. Are the problems too complicated? Am I unable to solve them without writing down the problem or using an IDE? If so, we reduce the complexity of the problems by modifying the parameters of the query. For example: early in development, problems were generated that required tracing through hundreds of 'for loop' iterations. I added a restriction in the query to set a maximum limit on inner 'for loop' iterations. This remains a difficult question to solve. The ast python package can find Python data structures, but creating a confidence interval for "complexity" is significantly more demanding, and is left for future work.
2. Is this code that a human would write to solve a real-world problem? Is the code able to be read by a human? For example: many nested comprehensions indicate unreadable code.
3. Does the code improve a students' ability to read code *that is not LLM generated?* This is one of my core research questions, and is still being investigated.

## Technical Considerations and Tradeoffs

#### Django versus Flask
Flask is typically used for smaller web projects, and Django and used for larger or more complex ones. I decided to use Django for several reasons. Firstly, it comes preloaded with useful features, like authentication, concurrent request handling, and database operations. I hadn't been exposed to either prior to this project, and Django leaves the door open for expansion into additional languages, gamification, or other features. The tradeoff is that Django has a higher learning curve, requiring more time until it's usable at the same proficiency as Flask.

#### ChatGPT and Anthropic versus other LLMs
ChatGPT's and Anthropic's APIs are straightforward to call, with clear documentation and transparent pricing schemes. They also offer multiple models that can be called depending on use case. For example, I call more robust and pricier models if the cheaper ones aren't doing the job.

#### "Vibe coding" web development
I built the frontend using HTML, CSS and Javascript. To accelerate development and implement more complex functionality, I collaborated with LLM tools like ChatGPT to generate JavaScript code. I iteratively tested, debugged, and adapted the provided code to ensure it aligned with my vision. While using ChatGPT allowed me to build features faster and focus on the overall product, I was mindful that it offered less opportunity to deepen my JavaScript skills on every line of code

#### Why the webapp generates Python instead of other languages
Python is widely accessible, approachable, and is becoming more popular with the rise of AI. And most importantly, Python is my strongest language. I can reliably test my webapp, determine the quality of generated code, and its usefulness and functionality. 

#### Latency and cost vs quality and accuracy
Sending queries to LLMs and receiving responses takes resources: latency, and cost. Each query takes several seconds and costs ~a tenth of a cent. If code valiation fails, we need to re-query the LLM. Each additional query gets us closer to the desired code, but worsens the user experience. As such, we cap the number of queries at three, and display the closest matching code to the user if all three queries fail. The tradeoff is that the user may receive code they weren't expecting, but I determined that receive code that was *close* is better than returning no code and an error message.

#### Exec() versus standalone environments
To verify if code returned by an LLM runs, I use Python's built-in exec() function, which directly executes the code. The output is read via the stdout() function from io, which is then stored and later used to check the user's submitted answer. exec() is known for being a potentially unsafe function to run, because it has no built-in safety checks. If a user can write and execute their own code in exec(), it can harm other users and irreparably damage data. To mitigate these risks, code is often run in isolated environments to prevent users maliciously accessing sensitive data. The tradeoff for safer code is a steeper learning curve, with slightly slower run times. exec() is typically faster, easier to set up, and requires no extra packages.

In our case, the user is never able to write and execute their own code with any of the current problem types. Users don't have control over queries either, so exec() is safe.

#### Prompt structure choices
Prompts are constructed modularly. A base query is defined and shared across all problem types, with additional constraints applied based on selected problem type and user specifications (subject, difficulty, etc.). The prompts primarly consist of explicit constraints in the form of "do" and "do not" instructions provided to the LLMs. 

The structure reduces maintenance overhead and promotes consistency across generated problems. Additionally, expressing constraints as explicit guidelines rather than paragraph-style instructions helps reduce ambiguity and lowers the likelihood of undesired outputs or hallucinations.

## HCI Considerations

#### Cognitive load
The platform is designed to keep cognitive load intentionally low, while directing attention toward tasks that support learning code comprehension. To this end, the problems and UI follow these principles:
1. Problems can be solved through mental execution rather than external tools
2. Only one problem is presented at a time
3. Each problem has a clear, recognizable goal
4. Problem structure remains consistent within each problem type

By minimizing variation and interface complexity, we ensure that cognitive effort are spent on understanding the code, rather than the surrounding environment or the instructions.

#### Iterative design and feedback loops
Feedback is given to the user in several ways, from intuitive button mapping, to receiving feedback on submitted answers. The following is a list of ways in which feedback loops are used:
1. Familiar UI affordances, such as visual button state changes to confirm user input
2. Immediate loading indicators when an action requires additional processing time
3. A history page that allows users to review past problems and track progress

These mappings set clear expectations for the user, and ensure every action is met with feedback.

#### Transparency of model behavior
The system is designed to be transparent, allowing users to understand its current state and predict how it will respond to actions. When errors or failure states occur, clear messages are presented to the user to explain what happened and how to respond. For example, users are notified that problems may generate that fail to meet their specifications. This transparency helps establish trust between the user and the system, even when edge cases arise.

#### Choice of problem types and subjects
Problem types are designed to specifically improve users' code comprehension skills. With that in mind, I designed and implemented 3 distinct problem types:
1. "Determine the output." Users predict the value produced when a given block of code is executed.
2. "Docstring writing." One or more functions are generated without explanatory text, and users are tasked with writing appropriate docstrings based on function behavior.
3. "Rearranging code." A block of code is presented with lines out of order, requiring users to rearrange them into a valid, executable sequence.

Across all problem types, users engage primarily in interpreting and reasoning about existing code, rather than producing original implementions. This ensures that the focus remains on code comrprehension as opposed to synthesis.

#### How UI choices affect model perception
The UI is designed to be as simple and navigable. In addition, the barrier to using the webapp is low; users are not required to be logged in to generate problems. The webapp has many features that support learning and mitigate distractions:
1. The UI is simple, with no clutter
2. The webapp can be used without an account
3. There are no popups
4. Each generated problem is centered
5. UI buttons are static

The above features contribute to the perception of a UI that is fast, usable, and reliable.

## Future Work
The following is a list of features either currently in development, or is planned for future versions:
1. **The accuracy and complexity of generated code.** The larger the number of constraints, the higher the likelihood of LLMs failing to generate code that matches user-defined specifications. Additional features that raise accuracy would be helpful to improve system stability and precision.
2. **Additional problem types.** The aforementioned problem types each contribute to the improving users' code comprehension skills. Additional types would be helpful to provide a more robust learning process.
3. **Boost backend efficiency.** Backend efficiency could be improved by implementing several features, such as caching, bulk querying, reducing redundant generation, and consolidating validation steps.
4. **Additional languages.** Expanding to Java, C++, C#, JavaScript, and C, would help the webapp reach a wider audience and appeal.
5. **Gamification features.** Adding features like expanded progress tracking, leaderboards, or achievements, would increase user engagement.