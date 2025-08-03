
//Adds method to retrieve csrf_token via cookies
//START CODE FROM CHATGPT
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

/* Adds listeners for sliders, retrieves values */
window.addEventListener('DOMContentLoaded', () => {
    const difficultySlider = document.getElementById('difficulty-slider');
    if (difficultySlider) {
        // restore saved value
        const storedValue = localStorage.getItem('difficultySlider');
        if (storedValue !== null) {
            difficultySlider.value = storedValue;
        }

        // saves on change (update local storage)
        difficultySlider.addEventListener('input', () => {
            localStorage.setItem('difficultySlider', difficultySlider.value);
        });
    }

    const problemLengthSlider = document.getElementById('problem-length-slider');
    if (problemLengthSlider) {
        const storedValue = localStorage.getItem('problemLengthSlider');
        if (storedValue !== null) {
            problemLengthSlider.value = storedValue;
        }

        problemLengthSlider.addEventListener('input', () => {
            localStorage.setItem('problemLengthSlider', problemLengthSlider.value);
        });
    }

    const checkboxStates = JSON.parse(localStorage.getItem('checkboxStates') || '{}');
    const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');

    // Restore saved states first
    allCheckboxes.forEach(cb => {
        if (checkboxStates.hasOwnProperty(cb.value)) {
            cb.checked = checkboxStates[cb.value];
        }
    });

    // Check if *any* subject-related checkboxes are checked
    const subjectCheckboxes = [...allCheckboxes].filter(cb =>
        ['physics', 'chemistry', 'biology', 'earth-science', 'computer-science', 'math', 'logic-and-reasoning', 'linguistics', 'geography', 'medicine-anatomy', 'adv-physics', 'adv-chemistry', 'adv-biology', 'adv-earth-science', 'adv-computer-science', 'adv-math'].includes(cb.id)
    );

    const anySubjectChecked = subjectCheckboxes.some(cb => cb.checked);

    if (!anySubjectChecked) {

        // No subject checked, default to computer-science and math
        ['computer-science', 'math'].forEach(id => {
            const cb = document.getElementById(id);
            if (cb) {
                cb.checked = true;
                checkboxStates[cb.value] = true;
            }
        });
        // Save the updated states
        localStorage.setItem('checkboxStates', JSON.stringify(checkboxStates));
    }

    // Add event listeners for saving changes
    allCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            checkboxStates[cb.value] = cb.checked;
            localStorage.setItem('checkboxStates', JSON.stringify(checkboxStates));
        });
    });
});

//variable for submitSkeleton delay
let loaderTimeout = null;

//adds event listener for generation options panel to open when clicked
if (!window.optionsButtonListenerAdded) {
    window.optionsButtonListenerAdded = true;

    document.addEventListener("DOMContentLoaded", function () {
        const button = document.getElementById('options-button');
        const panel = document.getElementById('generation-options-box');

        document.addEventListener('click', function (e) {
            const clickedInside = button.contains(e.target) || panel.contains(e.target);

            if (clickedInside) {
                if (button.contains(e.target)) {
                    const isOpen = button.classList.toggle('open');
                    panel.classList.toggle('open', isOpen);
                }
            } else {
                button.classList.remove('open');
                panel.classList.remove('open');
            }
        });
    });
}

//END CODE FROM CHATGPT



//debounce logic
let isFetching = false;

let initial_chatGPTresponse = "";
/** 
 * Called when a user clicks a difficulty button ("Easy", "Medium", "Hard").
 * Generates a problem for the user to solve.
 */
function fetchChatGPTResponse(retries=3, delay=1000) {

    //disables problem generation until current request is processed (and shown to user)
    if (isFetching) {
        console.log("Button press ignored; fetching in progress");
        return;
    }

    //debounce logic
    isFetching = true;

    //Define variables for relevant elements
    let chatResponseDiv = document.getElementById('chatgpt-response');
    let userInputDiv = document.getElementById('user-input-div');
    let userSubmit = document.getElementById('submit-answer');
    let feedbackMessage = document.getElementById("feedback");
    let hintsGroup = document.getElementById("hints-group");
    let hintsButton = document.getElementById("hints-button");
    let userInput = document.getElementById("user-input");
    let instructionsDiv = document.getElementById('instructions');
    let skeletonLoader = document.getElementById('skeleton-loader');
    let userInputAnswer = document.getElementById('user-input-answer');
    let resetButton = document.getElementById('reset-problem');
    let hints = document.getElementById("hints");
    let whyButton = document.getElementById("why-button");
    let explanation = document.getElementById("explanation");

    //setting defaults when button is clicked (removing submit and hint buttons, etc.)
    resetButton.style.visibility = 'hidden';
    userInputDiv.style.display = "none";
    userSubmit.style.display = "none";
    feedbackMessage.textContent = "";
    hintsGroup.style.visibility = "hidden";
    hintsGroup.style.display = "flex";
    hintsButton.style.display = "none";
    instructionsDiv.innerHTML = "";
    chatResponseDiv.innerHTML = "";
    skeletonLoader.style.display = 'block';
    whyButton.style.display = "none";
    explanation.style.display = "none";
    chatResponseDiv.contentEditable = "false";
    chatResponseDiv.autocomplete = "false";
    chatResponseDiv.spellcheck = false;

    const difficultySlider = document.getElementById('difficulty-slider');
    const problemLengthSlider = document.getElementById('problem-length-slider');
    const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
    const checkboxStates = {};
    allCheckboxes.forEach(cb => {
        checkboxStates[cb.value] = cb.checked;
    })

    const userSelections = {
        difficulty_level_slider: difficultySlider ? difficultySlider.value : null,
        problem_length_slider: problemLengthSlider ? problemLengthSlider.value : null,
        checkbox_states: checkboxStates,

    }

    //direct to /practice/, see urls.py for views.py function call
    fetch('/practice/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrftoken,
        },
        credentials: 'same-origin',

        //sends these variables to /practice/
        body: JSON.stringify({
            user_selections: userSelections,
        })
    })

    //when we get a response, do this
    .then(response => {

        //response is not okay, throw an error
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
            chatResponseDiv.innerHTML = "An error has occurred. Please try again or contact the administrator."
        }
        
        return response.json();
    })

    //we received data
    .then(data => {
        //info sent to user, no longer fetching request
        isFetching = false;

        userSubmit.style.display = "inline-block";
        userSubmit.style.visibility = "visible";
        userInputDiv.style.display = "inline-block";

        //START CODE FROM CHATGPT
        let existingSortable = document.getElementById("sortable-code-block");
        //console.log("existingSortable:", existingSortable);
        if (existingSortable) {
            const sortableInstance = Sortable.get(existingSortable);
            console.log("sortableInstance:", sortableInstance);
            if (sortableInstance) {
                sortableInstance.destroy();
                console.log("Sortable instance destroyed");
            }
            existingSortable.remove();
        }
        //END CODE FROM CHATGPT

        skeletonLoader.style.display = "none";
        userInput.value = "";
        hints.textContent = "";
        feedbackMessage.textContent = "";
        hintsGroup.style.visibility = "visible";
        hintsButton.style.visibility = "visible";
        hintsButton.style.display = "flex";

        //we received data from chatgpt
        if (data.chatgpt_response) {
            document.getElementById("problem-type").value = data.problem_type;
            document.getElementById("correct-answer").value = data.correct_answer;
            chatResponseDiv.classList.remove("highlight-drag-and-drop");
            chatResponseDiv.classList.add("highlight-default");

            //if problem type is "determine_output" (standard)
            if (document.getElementById("problem-type").value === "determine_output") {
                //format the output
                let formattedResponse = data.chatgpt_response
                .replace(/```(\w+)?\n([\s\S]+?)```/g, function(match, lang, code) {
                    lang = lang || 'plaintext';  // Default to plaintext if no language is specified
                    return `<pre><code class="language-${lang}">${code}</code></pre>`;
                });

                //set elements specific to "determine_output" problem type
                chatResponseDiv.innerHTML = `<p><strong> </strong></p>` + formattedResponse;
                instructionsDiv.innerHTML = "What printed value shows when the above code is ran? Remember that the 'output' variable is rounded to 3 decimals! Ex: 1.2468 -> 1.247"
                userInput.setAttribute("required", "true");
                userInput.style.display = "inline-block";
                userInputAnswer.style.display = "inline-block";

                //performs syntax highlighting
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                    });

            }
            //END CODE FROM CHATGPT

            //if problem type is "fill_in_vars"
            
            else if (document.getElementById("problem-type").value === "fill_in_vars") {
                let formattedResponse = data.chatgpt_response
                //START CODE FROM CHATGPT
                .replace(/```(\w+)?\n([\s\S]+?)```/g, function(match, lang, code) {
                    lang = lang || 'plaintext';  // Default to plaintext if no language is specified
                    return `<pre><code class="language-${lang}">${code}</code></pre>`;
                });
                //END CODE FROM CHATGPT

                //set elements specific to "fill_in_vars" problem type
                chatResponseDiv.innerHTML = `<p><strong> </strong></p>` + formattedResponse;
                document.getElementById("initial-response").value = chatResponseDiv.textContent;
                document.getElementById("initial-response-raw").value = chatResponseDiv.innerHTML;
                instructionsDiv.innerHTML = `Add docstrings to the code blocks above where indicted with triple quotation marks. Briefly summarize the code, then add parameters and return information. See the <a href="https://peps.python.org/pep-0257/" target="_blank" rel="noopener noreferrer" class="links">PEP 257 Docstring Conventions</a> for information on docstring structure. Note: phrasing differences are okay; the grader is lenient. Use the 'Reset Problem' button in the upper-right corner if you need to reload the original problem.`
                chatResponseDiv.contentEditable = "true";
                userInput.style.display = "none";
                userInputAnswer.style.display = "none";
                userInput.removeAttribute("required");
                resetButton.style.visibility = 'visible';

                //chatReponseDiv is editable, override default behavior of creating a div when the user presses enter

                //START CODE FROM CHATGPT
                if (!chatResponseDiv.hasAttribute("data-listener-attached")) {
                    chatResponseDiv.setAttribute("data-listener-attached", "true");
                    chatResponseDiv.addEventListener("keydown", function (event) {
                        if (event.key === "Enter") {
                            // event.preventDefault(); // Prevents default <div> insertion
                            // document.execCommand("insertLineBreak"); // Inserts a <br> instead
                            event.preventDefault();
                            // br = document.createElement("br");
                            const newline = document.createTextNode("\n");
                            const selection = window.getSelection();
                            if (!selection.rangeCount) return;

                            const range = selection.getRangeAt(0);
                            range.deleteContents();       // Remove any selected text (if any)
                            range.insertNode(newline);
                            //range.insertNode(br);         // Insert the <br> exactly where the cursor is

                            // Move the cursor (caret) after the inserted <br>
                            range.setStartAfter(newline);
                            range.setEndAfter(newline);
                            selection.removeAllRanges();
                            selection.addRange(range);
                        }
                        //END CODE FROM CHATGPT

                        if (event.key === "Tab") {
                            event.preventDefault();
                            const selection = window.getSelection();
                            if (!selection.rangeCount) return;

                            const range = selection.getRangeAt(0);
                            const fourSpaces = document.createTextNode("    ");
                            range.deleteContents();
                            range.insertNode(fourSpaces);

                            range.setStartAfter(fourSpaces);
                            range.setEndAfter(fourSpaces);
                            selection.removeAllRanges();
                            selection.addRange(range);
                        }
                });
            }
                

                //performs syntax hightlighting
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                    });
                }

            else if (document.getElementById("problem-type").value == "drag_and_drop") {
                //set elements specific to "drag_and_drop" problem type
                chatResponseDiv.classList.remove("highlight-default");
                chatResponseDiv.classList.add("highlight-drag-and-drop");
                instructionsDiv.innerHTML = "Rearrange the above code so it runs correctly by dragging and dropping each line, then click Submit. Small differences in order (declaring variables, for example) do not matter; the grader is lenient.";
                userInput.style.display = "none";
                userInputAnswer.style.display = "none";
                userInput.removeAttribute("required");

                //START CODE FROM CHATGPT
                //separate each line of code
                let codeLines = data.chatgpt_response.split("\n").filter(line => line.trim() !== "");

                //create a div container for each line of code
                let container = document.createElement("div");

                //setting attributes for each div
                container.id = "sortable-code-block";
                container.style.display = "flex";
                container.style.flexDirection = "column";
                container.style.gap = "2px";
                container.style.marginTop = "5px";
                container.style.marginBottom = "10px";

                codeLines.forEach((line, index) => {
                    let block = document.createElement("div");
                    block.className = "draggable-line";
                    block.setAttribute("data-index", index);
                    
                    // Create the pre and code tags for code highlighting
                    let codeContainer = document.createElement("pre");
                    let codeElement = document.createElement("code");
                    codeElement.className = "language-python";
                    codeElement.textContent = line;
                    
                    // Apply styles to remove unwanted borders/padding
                    codeContainer.style.margin = "0"; // Remove margin
                    codeContainer.style.padding = "0"; // Remove padding
                    codeElement.style.margin = "0"; // Remove margin from code
                    codeElement.style.padding = "0"; // Remove padding from code
                    
                    // Append the code element to the pre container, and then the pre container to the block
                    codeContainer.appendChild(codeElement);
                    block.appendChild(codeContainer);

                    // Style the block itself
                    block.style.padding = "5px 2px";
                    block.style.border = "none";
                    block.style.backgroundColor = "#222223";
                    block.style.cursor = "move";
                    block.style.margin = "0";
                    block.style.boxSizing = "border-box"; // Make sure padding is within the width

                    // Add the block to the container
                    container.appendChild(block);
                });

                // Add div to the container
                chatResponseDiv.appendChild(container);

                // Use a small timeout to let the DOM update/render
                setTimeout(() => {
                    const sortableTarget = document.querySelector("#sortable-code-block");
                    
                    if (!sortableTarget) {
                        console.warn("Sortable container not found!");
                        return;
                    }

                    Sortable.create(sortableTarget, {
                        animation: 150,
                    });

                }, 50);

                //END CODE FROM CHATGPT

                // Save original output if needed for answer checking
                document.getElementById("initial-response").value = data.unmixed_lines;

                document.querySelectorAll('.draggable-line pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });

            }

        }

        //there was an error retrieving the chatgpt data, throw an error
        else {
            chatResponseDiv.innerHTML = `<p style="color: red;">Error: ${data.error || 'Unknown error'}</p>`;
        }

    })

    //START CODE FROM CHATGPT
    //there was an error retreiving data
    .catch(error => {

        //set isFetching to false so we can try again
        isFetching = false;
        if (retries > 0) {
        // Retry with exponential backoff
        console.log(`Retrying... Attempts left: ${retries}`);
        setTimeout(() => {
            fetchChatGPTResponse(retries - 1, delay * 2); // Increase delay for next attempt
        }, delay);

        } else {
            skeletonLoader.style.display = "none";
            // Show error message after max retries are reached
            console.error('Request failed after multiple attempts. ', error);
            document.getElementById('chatgpt-response').innerHTML = '<p style="color: red;">Failed to fetch response from ChatGPT after several attempts.</p>';
        }
    });
    //END CODE FROM CHATGPT
}

/**
 * Called when user clicks the Submit button.
 * Calls into functions that check the user's input against the correct answer.
 */ 
function submitUserAnswer() {
    const userSubmit = document.getElementById('submit-answer');
    const difficulty = document.getElementById('difficulty').value;
    const hintsButton = document.getElementById("hints-button");
    const problemType = document.getElementById("problem-type").value;
    const whyButton = document.getElementById("why-button");
    const hintsGroup = document.getElementById("hints-group");
    const resetProblem = document.getElementById("reset-problem");
    const feedbackMessage = document.getElementById("feedback");
    let submitSkeleton = document.getElementById("submit-skeleton-loader");
    //submitSkeleton.style.display = 'inline-block';

    // Delay showing the submit skeleton loader
    let loaderShown = false;
    let loaderTimeout = setTimeout(() => {
        if (!loaderShown) {
            submitSkeleton.style.display = 'inline-block';
            loaderShown = true;
        }
    }, 200);

    let url = "";
    let data = {
        difficulty: difficulty,
        problem_type: problemType,
        correct_answer: document.getElementById("correct-answer")?.value || null,
    };

    try {
        if (problemType === "determine_output") {
            url = "/practice/check-answer/";
            data.user_input = document.getElementById("user-input").value;
        }

        else if (problemType === "fill_in_vars") {
            url = "/practice/check-answer-fill-in-vars/";
            data.user_input = document.getElementById("chatgpt-response").textContent;
            data.initial_chatGPTResponse = document.getElementById("initial-response").value;
        }

        else if (problemType === "drag_and_drop") {
            url = "/practice/check-answer-drag-and-drop/";
            const blocks = document.querySelectorAll('#sortable-code-block .draggable-line code');
            const codeLines = Array.from(blocks).map(code => code.textContent);
            const finalCode = codeLines.join('\n');

            data.user_input = finalCode;
            data.final_code = finalCode;
            data.initial_chatGPTResponse = document.getElementById("initial-response").value;
            
        }

        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": csrftoken
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            clearTimeout(loaderTimeout);
            submitSkeleton.style.display = 'none';
            loaderShown = false;
            if (data.message.includes("Correct")) {
                feedbackMessage.textContent = "Correct!";
                feedbackMessage.style.color = "#6eff6e";
                userSubmit.style.display = "none";
                userSubmit.style.visibility = "hidden";
                hintsButton.style.visibility = "hidden";
                hints.innerHTML = "";
                hintsGroup.style.display = "none";
                whyButton.style.display = "flex";
                whyButton.style.visibility = "visible";
                resetProblem.style.visibility = "hidden";
            } else {
                feedbackMessage.textContent = data.message || "Incorrect";
                feedbackMessage.style.color = "#f74364";
                userSubmit.style.display = "inline-block";
            }
        });

    } catch (error) {
        clearTimeout(loaderTimeout);
        submitSkeleton.style.display = 'none';
        loaderShown = false;
        console.error("Error during submission:", error);
    }
}

/**
 * Sets the difficulty of the hidden element, 'difficulty'
 */ 
function setDifficulty(level) {
    document.getElementById("difficulty").value = level;
}

/**
 * Handles the button press; gets response from backend
 */ 
function handleButtonPress() {
    //retrieve session data, see which prompt was generated
    fetchChatGPTResponse()
    //setDifficulty(difficultyLevel)
    
}

//stores information for all preset buttons
const presets = {
    easy: {
        difficulty: 1,
        problemLength: 1,
        checkboxes: {
            "enumerate": false,
            "zip": false,
            "any/all": false,
            "map/filter": false,
            "data-slicing": false,
            "comprehensions": false,
            "lambda-functions": false,
            "args-and-kwargs": false,
        }
    },

    medium: {
        difficulty: 2,
        problemLength: 3,
        checkboxes: {
            "enumerate": true,
            "zip": true,
            "any/all": false,
            "map/filter": false,
            "data-slicing": true,
            "comprehensions": true,
            "lambda-functions": false,
            "args-and-kwargs": false,
        }
    },

    hard: {
        difficulty: 3,
        problemLength: 7,
        checkboxes: {
            "enumerate": true,
            "zip": true,
            "any/all": true,
            "map/filter": true,
            "data-slicing": true,
            "comprehensions": true,
            "lambda-functions": true,
            "args-and-kwargs": true,
        }
    }
}

//applies presets
function applyPreset(presetName) {
    const preset = presets[presetName];
    if (!preset) return

    //update sliders
    document.getElementById("difficulty-slider").value = preset.difficulty;
    document.getElementById("problem-length-slider").value = preset.problemLength;

    //update checkboxes
    const allCheckboxes = document.querySelectorAll('input[type=checkbox]');
    allCheckboxes.forEach(cb => {
        if (preset.checkboxes.hasOwnProperty(cb.value)) {
            cb.checked = preset.checkboxes[cb.value];
        }
    })

    //update local storage
    localStorage.setItem('difficultySlider', preset.difficulty);
    localStorage.setItem('problemLengthSlider', preset.problemLength);
    localStorage.setItem('checkboxStates', JSON.stringify(preset.checkboxes));
}

/**
 * Called when the user clicks the 'Get a hint!' button.
 * Sends a query to ChatGPT that returns a hint for the user.
 */
function generateHint() {
    let hints = document.getElementById("hints");
    let userInput = document.getElementById("user-input").value;
    var chatResponseDiv = document.getElementById('chatgpt-response').textContent;
    //let difficultyLevel = document.getElementById('difficulty').value;
    let problemType = document.getElementById('problem-type').value;

    let hintsSkeletonLoader = document.getElementById('hints-skeleton-loader');
    hintsSkeletonLoader.style.display = "inline-block";
    hints.textContent = "";

    fetch("/practice/generate-hint/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrftoken
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            user_input: userInput,
            //difficulty: difficultyLevel,
            chatGPTResponse: chatResponseDiv,
            problem_type: problemType,
        })
    })

    .then(response => response.json())
    .then(data => {
        hintsSkeletonLoader.style.display = "none";
        let hintText = data.message;
        //START CODE FROM CHATGPT
        hintText = hintText.replace(/`([^`]+)`/g, '<code>$1</code>');
        //END CODE FROM CHATGPT
        hints.innerHTML = hintText;
        
        
    })
    .catch(error => console.error("Error:", error));
    
}

function handleResetProblem() {
    let chatResponseDiv = document.getElementById('chatgpt-response');
    chatResponseDiv.innerHTML = document.getElementById('initial-response-raw').value;
    hljs.highlightAll();
}

//START CODE FROM CHATGPT
document.addEventListener("DOMContentLoaded", function () {
    let userInputField = document.getElementById("user-input");
    let feedbackMessage = document.getElementById("feedback");
    let chatgptResponse = document.getElementById("chatgpt-response");

    if (userInputField) {
        userInputField.addEventListener("input", function () {
            //END CODE FROM CHATGPT
            feedbackMessage.textContent = "";
        });
    }

    if (chatgptResponse) {
        chatgptResponse.addEventListener("input", function () {
            feedbackMessage.textContent = "";
        })
    }

});

function generateExplanation() {
    let userInput = document.getElementById("user-input").value;
    var chatResponseDiv = document.getElementById('chatgpt-response').textContent;
    let whyButton = document.getElementById('why-button');
    let problemType = document.getElementById("problem-type").value;
    let correctAnswer = document.getElementById("correct-answer").value;
    let explanationSkeletonLoader = document.getElementById('explanation-skeleton-loader');
    explanationSkeletonLoader.style.display = "inline-block";

    fetch("/practice/generate-explanation/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrftoken,
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            user_input: userInput,
            chatGPTResponse: chatResponseDiv,
            problem_type: problemType,
            correct_answer: correctAnswer,
        })
    })

    .then(response => response.json())
    .then(data => {
        explanationSkeletonLoader.style.display = "none";
        let explanation = document.getElementById("explanation");
        let explanationText = data.message;
        //START CODE FROM CHATGPT
        explanationText = explanationText.replace(/`([^`]+)`/g, '<code>$1</code>');
        //END CODE FROM CHATGPT
        explanation.innerHTML = explanationText;
        whyButton.style.visibility = 'hidden';
        explanation.style.display = 'block';
        
    })
    .catch(error => console.error("Error:", error));

}