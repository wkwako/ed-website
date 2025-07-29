import requests
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from . import utilities
from .models import UserHistory
import re
from io import StringIO
from contextlib import redirect_stdout
import ast
import copy
import asyncio
import aiohttp

#STUFF TO FIX:
#TODO: make spacing between task bar items flexible
#TODO: on create account page, should center more stuff. round boxes, etc.
#TODO: add options page/section for users
#TODO: make sure you've cited chatgpt correctly (and in the right spots)

#TODO: problem type: multiple choice
#TODO: problem type: re-arrange blocks of code to work
#TODO: problem type: fix algorithmic error in standard CS algorithm

#other ideas for problems:
#1. chatgpt generates code, user must provide a brief description of fns and summary of what code is doing
#2. chatgpt generates code with random varible names, user must replace var names with better names
#3. chatgpt generates incorrect code, user must find the error(s) in the code

def home(request):
    """Returns the home page, home.html."""
    return render(request, 'edtech_project/home.html')

#START CODE FROM CHATGPT
def practice(request):
    """Returns the practice page, practice.html.
       Also contains logic for generating coding problems."""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            request.session["correct_answer"] = None
            body = json.loads(request.body)
            #query = body.get("message", "An error has occurred when generating the query.")
            temperature = 1.0
            difficultyLevel = body.get('difficulty_level', 'undefined')
            #print (difficultyLevel)

            user_selections = body.get('user_selections', None)
            # print (f'USER SELECTIONS: {user_selections}')
            # print (f'TYPE OF USER SELECTIONS: {type(user_selections)}')
            # print (user_selections['difficulty_level'])
            # print (user_selections['checkbox_states']['functions'])

            print (f'USER SELECTIONS: {user_selections}')

            #print (utilities.process_user_selections_problem_length(user_selections))
            print (utilities.process_user_selections_structures_and_difficulty(user_selections))
            print (utilities.process_user_selections_subjects(user_selections))

            #END CODE FROM CHATGPT
            problem_type,query = utilities.get_query(difficultyLevel, user_selections)

            #set problem text to None
            request.session["problem_text"] = None

            #query chatgpt and validate its response
            result, chatgpt_text, err, output = utilities.validate_and_query(request, query, temperature, problem_type)

            unmixed_lines = ""


            if problem_type == "fill_in_vars":

                #filter out halluciations in chatgpt_text (look for/remove extra set of docstrings)
                lines_to_remove = []
                code_lines = chatgpt_text.splitlines()
                for i, line in enumerate(code_lines):
                    if line.strip() in ["\"\"\" \"\"\"", "\"\"\"\"\"\""]:
                        lines_to_remove.append(i)

                for i in lines_to_remove[::-1]:
                    del code_lines[i]

                #reform text without hallucinations
                chatgpt_text = '\n'.join(code_lines)

                #set 'correct answer' as current chatgpt_text
                output = chatgpt_text

                #remove docstring text, keep triple quotations
                indices = [m.start() for m in re.finditer('\"\"\"', chatgpt_text)]
                for i in range(len(indices))[::-2]:
                    start = indices[i-1]
                    end = indices[i]
                    chatgpt_text = chatgpt_text[:start+3] + ' ' + chatgpt_text[end:]

            elif problem_type == "drag_and_drop":
                chatgpt_text = chatgpt_text[9:-3]
                #code_lines = chatgpt_text.split("\n")
                #print (f'CODE LINES: {code_lines}')
                #exclusions = utilities.lines_to_exclude(code_lines)
                #print (f'EXCLUSIONS: {exclusions}')
                unmixed_lines = copy.deepcopy(chatgpt_text)
                chatgpt_text = utilities.mix_lines(chatgpt_text)

            #code is valid
            if result:
                if problem_type != "fill_in_vars":
                    print (f'previous correct answer: {output}')
                    output = utilities.normalize_output_answer(output)
                    print (f'normalized correct answer: {output}')
                    request.session["correct_answer"] = output

                #variables that are sent back to the front end, processed by xhr.load()
                #print (f'SENDING BACK CORRECT ANSWER AS: {output}')
                return JsonResponse({
                    "chatgpt_response": chatgpt_text,
                    "problem_type": problem_type,
                    "correct_answer": output,
                    "unmixed_lines": unmixed_lines,
                    })
            
            #code is not valid
            return JsonResponse({
                "chatgpt_response": err,
                "problem_type": err,
                })
            
        #something has gone terribly wrong
        except Exception as exception:
            msg = str(exception)
            code = hasattr(exception, 'response')
    #if not a POST request, render the home page template normally
    return render(request, 'edtech_project/practice.html')

@login_required
def history(request):
    """Returns the history page, history.html."""
    #if more data is needed for history.html, here are the steps to do that:
    # 1. get needed info in a variable accessible in utilities.py
    # 2. add the field in models.py to UserHistory
    # 3. add code for storing the data in store_in_db
    # 4. migrate changes
    # 5. use the data in history.html

    context = {}
    
    #selects the most recent attempted problems, up to 20.
    user_history = UserHistory.objects.filter(user=request.user).order_by("-timestamp")[:20]

    #determines the number of most recently attempted problems, up to 20
    context["num_entries"] = len(user_history)

    #determines the number of correct problems
    context["num_correct"] = len([entry for entry in user_history if entry.is_correct])
    context["history"] = user_history
    return render(request, 'edtech_project/history.html', context)

class CreateAccount(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/create_account.html"

def check_answer(request):
    """Checks a user's answer for the 'determine_output' problem type."""
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("user_input", None).strip()
        correct_answer = request.session.get("correct_answer")
        problem_type = data.get("problem_type", "")
        #print (f"problem type for model is: {problem_type}")

        #correct_answer is None. something has gone terribly wrong
        if not correct_answer:
            return JsonResponse({"success": False, "error": "Answer is None. Start debugging in utilities.validate_and_query()"}, status=400)
        
        is_user_correct = user_input == correct_answer

        #prepare to store data in db
        current_user = request.user
        difficulty = data.get("difficulty")

        problem_text = request.session.get("problem_text", "")[10:-3]

        #stores the problem in the db
        utilities.store_in_db(request, current_user, difficulty, problem_text, is_user_correct, problem_type, correct_answer)

        #user is correct, send 'Correct!' message to frontend
        if is_user_correct:
            return JsonResponse({"success": True, "message": "Correct!"})
        
        #user was not correct, send 'Incorrect' message back to frontend
        else:
            return JsonResponse({"success": True, "message": "Incorrect. Please try again."})

    return JsonResponse({"success": False, "error": "Request method was not POST"}, status=405)

def safety_checks(user_input, initial_chatGPTResponse):
    """Performs safety checks when executing user-generated code. Checks for unsafe functions,
       imports modules, infinite loops, line count differences, and internal variable calls."""
    #START CODE FROM CHATGPT
    blocked_functions = {'exec', 'eval', 'input', 'open', 'os', 'system', 'socket', 'urllib', 'requests'}
    blocked_modules = {'socket', 'os', 'sys', 'subprocess', 'shutil'}
    tree = ast.parse(user_input)

    try:
        for node in ast.walk(tree):

            #checks for unsafe functions
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in blocked_functions:
                    return False, "Error: disallowed functions used"
                
            #checks for unsafe imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in blocked_modules:
                        return False, "Error: disallowed import used"
            
            #checks for unsafe modules
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name) and node.value.id in blocked_modules:
                    return False, "Error: disallowed modules used"
    except:
        return False, "Error analyzing code"
    #END CODE FROM CHATGPT
    
    #checks for calls to internal variables that should not be accessed
    # if "__" in user_input:
    #     return False, "Double underscores detected, please rename your variables"
    
    #checks for infinite loops
    #START CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
    if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
        #END CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
        return False, "Error: infinite loop detected"
    
    

    #checks for total line difference between user's answer and original problem
    #need to take this line out. instead, find where line differences start and stop. make sure all the new ones are strings
    
    #get all lines that are different from original
    initial_lines = initial_chatGPTResponse.split("\n")
    user_lines = user_input.split("\n")
    new_indices = []
    
    #'i' is position in initial_lines, 'j' is position in user_lines
    i = 0
    j = 0
    while i < len(initial_lines):
        #code lines are equal, go to next indices in both lists
        if user_lines[i].strip() == initial_lines[i].strip():
            i += 1
            j += 1
        #code lines are not equal
        else:
            #this user line must have been modified
            new_indices.append(j)
            #i and j are the same, so original line was modified
            if i == j:
                i += 1
                j += 1
            #completely new line, increment only j to 'catch up' to initial_lines
            else:
                j += 1

    #TODO: check that all these lines are only strings?
    for idx in new_indices:
        if type(user_lines[idx]) != str:
            return False, "Error: non-strings detected in user-modified code."

    return True, "Code passed initial safety checks"

def check_answer_fill_in_vars(request):
    """Checks a user's answer for the 'fill_in_vars' problem type."""
    if request.method == "POST":
        print ('CHECK ANSWER STARTING')
        reply = None
        data = json.loads(request.body)
        user_input = data.get("user_input", "")
        difficultyLevel = data.get("difficulty", "undefined")
        initial_chatGPTResponse = data.get("initial_chatGPTResponse", "")
        problem_type = data.get("problem_type", "")
        correct_answer = data.get("correct_answer", "")[9:-3]

        print (f'USER ANSWER: {user_input}')
        print (f'CORRECT ANSWER: {correct_answer}')

        #removing whitespace at start of code
        while user_input[0] == " ":
            user_input = user_input[1:]

        while initial_chatGPTResponse[0] == " ":
            initial_chatGPTResponse = initial_chatGPTResponse[1:]

        #user has not attempted the problem
        if user_input == initial_chatGPTResponse:
            reply = "The code has not yet been modified."
            return JsonResponse({"success": True, "message": reply})

        #performs safety checks
        print ('STARTING SAFETY CHECKS')
        result,msg = safety_checks(user_input, initial_chatGPTResponse)
        print ('ENDING SAFETY CHECKS')
        if not result:
            #code was not safe, return error message to user
            return JsonResponse({"success": True, "message": msg})

        #code is safe to run
        # try:
        #     #calculates the output of the user-edited code
        #     f = StringIO()
        #     with redirect_stdout(f):
        #         local_vars = {}
        #         exec(user_input, local_vars, local_vars)
        #         output1 = f.getvalue()

        #     #calculates the output of the original code
        #     f = StringIO()
        #     with redirect_stdout(f):
        #         local_vars = {}
        #         exec(initial_chatGPTResponse, local_vars, local_vars)
        #         output2 = f.getvalue()

        #     #original code and user-edited code should produce the same result
        #     if output1 != output2:
        #         reply = "The output of the code is different from its original. Please use the restart button to try again."
        #         return JsonResponse({"success": True, "message": reply})
            
        # except:
        #     reply = "Error: the code could not be run."
        #     return JsonResponse({"success": True, "message": reply})
        
        #query = f"I gave a student this block of python code: {initial_chatGPTResponse}. The goal is for them to fill in the functions and variables named 'mystery1' etc. and 'unknown1' etc so that these function and variable names no longer exist. I would like you to analyze how they did. Here is the finished code they submitted: {user_input}. Please grade leniently, but accurately. Please output 'Correct' if the functions and variables are correctly named (i.e. approximating what the function is actually doing), and 'Incorrect' if not. I do not care about the contents of the function. ONLY judge them on these variable names. If the answer is Incorrect, please provide a short hint for the student about what they got wrong, but without explicitely giving them the answer (i.e. telling them what the function does). For example, if a student named all functions correctly but forgot to change the name in function calls, tell them that."
        query = f"I gave a student this block of python code: {initial_chatGPTResponse}. The goal is for them to add docstrings to the code that make sense and adhere to the PEP8 style conventions. I would like you to analyze how they did. Here is the finished code they submitted: {user_input}. Please grade leniently, but accurately. Do not grade on small formatting issues, like whitespace. Please output ONLY \"Correct\"' if the docstrings correctly summarize each function/class, and \"Incorrect.\" if not. ONLY judge the docstring content, not the function content. If the answer is Incorrect, please provide a short hint (1-2 short sentences) for the student about what they got wrong, but without explicitely giving them the answer (i.e. telling them what the function does). Do not introduce the hint with \"Hint\", just provide it after \"Incorrect.\". Do not mention the student in the hint. The first word of your response MUST be either \"Correct\" or \"Incorrect.\""
        temperature = 0.3

        #query_test = asyncio.run(utilities.double_query("Please output the words, \"this is a test\""))
        #print (f'QUERY TEST IS: {query_test}')
        #return JsonResponse({"success": True, "message": query_test[0] + query_test[1]})

        replies = asyncio.run(utilities.double_query(query, temperature))

        is_user_correct = replies[1] == "Correct"
        reply = replies[1]
        
        # is_user_correct = (replies[0] == "Correct") and (replies[1] == "Correct")
        # if not is_user_correct:
        #     if replies[1][:2] == "In":

        #         reply = replies[1]
        #     else:
        #         reply = replies[0]

        # else:
        #     reply = "Correct"

        # print (f'CHATGPT RESPONSE: {replies[0]}')
        # print (f'ANTHROPIC RESPONSE: {replies[1]}')
        # print (f'REPLY: {reply}')

        print (f'REPLIES: {replies}')

        # reply = utilities.chatgpt_query(query, temperature)
        # is_user_correct = reply == "Correct"

        

        #need to ask chatGPT to generate correct_code
        current_user = request.user
        utilities.store_in_db(request, current_user, difficultyLevel, user_input, is_user_correct, problem_type, correct_answer)

        return JsonResponse({"success": True, "message": reply})

    return JsonResponse({"success": False, "error": "Request method was not POST"}, status=405)

def check_answer_drag_and_drop(request):
    #TODO: answer is rounded on backend, but submitted answer is not rounded.
    #should probably fix this by formatting submitted code answer, then comparing to
    #formatted code before mixup
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("user_input", "")
        difficultyLevel = data.get("difficulty", "undefined")
        initial_chatGPTResponse = data.get("initial_chatGPTResponse", "")
        problem_type = data.get("problem_type", "")
        final_code = data.get("final_code", "")
        correct_answer = data.get("correct_answer", "")
        current_user = request.user

        f = StringIO()
        with redirect_stdout(f):
            try:
                local_vars = {}
                exec(final_code, local_vars, local_vars)

            except:
                #stores the problem in the db
                utilities.store_in_db(request, current_user, difficultyLevel, final_code, False, problem_type, initial_chatGPTResponse)
                return JsonResponse({"success": True, "message": "Incorrect"})
            
        output = f.getvalue()
        if output.strip() == correct_answer.strip():
            #stores the problem in the db
            utilities.store_in_db(request, current_user, difficultyLevel, final_code, True, problem_type, initial_chatGPTResponse)
            return JsonResponse({"success": True, "message": "Correct!"})
        
        #stores the problem in the db
        utilities.store_in_db(request, current_user, difficultyLevel, final_code, True, problem_type, initial_chatGPTResponse)
        return JsonResponse({"success": True, "message": "Correct!"})

        # try:
        #     f = StringIO()
        #     with redirect_stdout(f):
        #         print ("inside stdout")
        #         local_vars = {}
        #         print ("about to run exec()")
        #         exec(final_code, local_vars, local_vars)
        #         output = f.getvalue()

        #         print (f'correct answer: {correct_answer}')
        #         print (f'user answer: {output}')

        #         if output == correct_answer:
        #             return JsonResponse({"success": True, "message": "Correct!"})

        # except:
        #     return JsonResponse({"success": True, "message": "Incorrect"})

        

    
    return JsonResponse({"success": False, "error": "Reqeuest method was not POST"}, status=405)

def generate_hint(request):
    """Generates a hint for the user based on the problem type."""
    if request.method == "POST":
        data = json.loads(request.body)
        difficultyLevel = data.get("difficulty", "undefined")
        user_input = data.get("user_input", "")
        chatGPT_response = data.get("chatGPTResponse")
        problem_type = data.get("problem_type")
        query = chatGPT_response + "\n I've given this coding problem to a student."

        if problem_type == "determine_output":
            query += f" The student is tasking with determining the output. I know that the answer is {request.session.get('correct_answer')}. What one single hint would you give them to help them figure out what the answer is?"
            
            #user has attempted the problem, provide a more specific hint.
            if user_input:
                query += f"The answer they've provided is {user_input}. What single tip would you give to them, specific to their input, that could help them figure out the answer?"
            
            query += " Do not give them the actual answer."

        #creates a hint for the fill_in_vars problem type. need to be more careful here so GPT doesn't give
        #away the answer.
        elif problem_type == "fill_in_vars":
            query += " The goal of this coding assignment is for the student to add docstrings to the code describing what it does. To this end, they must understand the code to successfully write these docstrings. What one single tip would you give to this student that might help them understand the different functions and classes in the code? Do not give a generic hint like 'think about what each function is doing'. Do not directly tell them what the functions are doing, but guide them in the right direction."
        
        query +=  " Do not include an intro to the tip, like, /'the tip I would suggest is:/'."

        temperature = 1
        hint = utilities.chatgpt_query(query, temperature)
        
        return JsonResponse({"success": True, "message": hint})
    
    return JsonResponse({"success": False, "error": "Request method was not POST"}, status=405)

def generate_explanation(request):
    """Generates an explanation for why the correct answer was correct. Only available to the user
       after they get the problem right. Only callable once per problem."""
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("user_input", "")
        chatGPT_response = data.get("chatGPTResponse", "")
        problem_type = data.get("problem_type", "")
        correct_answer = data.get("correct_answer","")
        query = chatGPT_response + "\nThis is a Python coding problem I've given to a student. "
        instructions1 = " I need you to create an explanation for why this is the right answer."
        restrictions1 = "Including function and variable names in your explanation is okay, but do not include multiple lines of code. Your explanation cannot be longer than 150 words."

        type_instructions = None
        explanation_focus = None
        if problem_type == "determine_output":
            type_instructions = f" In this particular problem, the student was tasked with determining the output of the code. The answer to this problem is {correct_answer}, which the student got correct."
            explanation_focus = " Please focus your explanation on why the code produces this output."

        elif problem_type == "fill_in_vars":
            type_instructions = f" In this particular problem, the student was tasked with writing docstrings for each core function and class, which the student has done successfully. Here is their submitted answer: {correct_answer}."
            explanation_focus = " Please focus your explanation on what each function does. Do not mention the student, just explain the code."

        elif problem_type == "drag_and_drop":
            type_instructions = f" In this particular problem, the student was tasked with re-arranging each line so the code runs correctly and produces an output of {correct_answer}, which the student has done successfully."
            explanation_focus = " Please focus your explanation on why the code produces this output."

        query += type_instructions + explanation_focus + instructions1 + restrictions1

        temperature = 0.3
        message = utilities.chatgpt_query(query, temperature)
        print (f'MESSAGE BEFORE MODIFICATION: {message}')

        check_instructions = " I need you to determine if the explanation for the code is sufficient. Could a Python beginner or intermediate understand the explanation? Is it clearly explained? Is it describing what the code is actually doing? etc. Please output \"Sufficient.\" and nothing else if the explanation is okay as-is. If the explanation is not okay, then provide a better explanation. Do not introduce the explanation, just provide it. The limit for this explanation is 150 words."
        explanation_check = query + type_instructions + check_instructions
        check_message = utilities.anthropic_query(query, temperature)
        if check_message[0] != "S":
            #message is not okay. modify message
            message = check_message

        print (f'MESSAGE AFTER MODIFICATION: {message}')

        return JsonResponse({"success": True, "message": message})

    return JsonResponse({"success": False, "error": "Request method was not POST"}, status=405)