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
To provide the user as consistent an experience as possible, queries must be finely tuned to produce similarly-structured code with each generate. Even the shortest queries are several hundred words long, 

For example, the name of the variable users examine is always called "output". variable "output" is always used as the 

-even shortest prompts are several hundred words -> required for extreme consistency
-structured into "dos" and "donts" decreases chance for AI to hallucinate


## HCI Considerations

#### Cognitive load
-problems should be able to be solved via mental math and calculations
-only one problem displayed at a time
-easily understandable
-structure of each problem is always similar. output variable always used, etc.

#### Iterative design and feedback loops
-what feedback does the user receive?
-simple button depresses to error messages
-history section


#### Transparency of model behavior
-we tell the user that a problem matching their specifications may be generated
-undersell so user doesn't feel deceived
-show user all error messages when something doesn't work

#### Choice of problem types and subjects
-focusing directly on code comprehension
-talk about each of the 3 problem types here and how they help

#### How UI choices affect model perception

The UI is designed to be as simple and navigable is possible. The barrier to entry is low; users are not required to log in to generate problems, 

The UI is as simple as possible to keep user focus on coding problems.
-very simple UI
-can be used without a login
-no pop up windows
-nothing clouding screen
-screen is focused
-UI buttons do not jump around
-not glamorous, but fast, usable, and reliable

#### Aligning System Behavior with User Expectations
-again, undersell so user doesn't feel deceived


## Future Work
-accuracy, subject variety, complexity
-more languages
-more safety features: currently using exec(), etc.
-caching, bulk querying, sharding, load balancing
