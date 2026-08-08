import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import ast
from django.contrib.auth.models import User
from .models import UserHistory
import random
import re
import hashlib
import asyncio
import aiohttp
from io import StringIO
import anthropic
import copy
from . import static_variables
from contextlib import redirect_stdout
import openai

#START CODE FROM CHATGPT
def detect_structures(code: str):
    class StructureVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found = {
                "enumerate": False,
                "zip": False,
                "any-all": False,
                "map-filter": False,
                "set-operations": False,
                "data-slicing": False,
                "conditional-chaining": False,
                "comprehensions": False,
                "lambda-functions": False,
                "args-and-kwargs": False,
                "nested for loops": False,
                "for loops": False,
                "while loops": False,
            }
            self.loop_depth = 0
            self.while_loop_depth = 0

        def visit_Call(self, node):
            # enumerate
            if isinstance(node.func, ast.Name) and node.func.id == "enumerate":
                self.found["enumerate"] = True
            # zip
            if isinstance(node.func, ast.Name) and node.func.id == "zip":
                self.found["zip"] = True
            # any/all
            if isinstance(node.func, ast.Name) and node.func.id in {"any", "all"}:
                self.found["any-all"] = True
            # map/filter
            if isinstance(node.func, ast.Name) and node.func.id in {"map", "filter"}:
                self.found["map-filter"] = True
            self.generic_visit(node)

        def visit_BinOp(self, node):
            # set operations: union |, intersection &, difference -, symmetric difference ^
            if isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.Sub, ast.BitXor)):
                if isinstance(node.left, ast.Set) or isinstance(node.right, ast.Set):
                    self.found["set-operations"] = True
            self.generic_visit(node)

        def visit_Subscript(self, node):
            # data slicing (e.g., a[1:3])
            if isinstance(node.slice, ast.Slice):
                self.found["data-slicing"] = True
            self.generic_visit(node)

        def visit_If(self, node):
            # conditional chaining: if ... elif ...
            if any(isinstance(orelse, ast.If) for orelse in node.orelse):
                self.found["conditional-chaining"] = True
            self.generic_visit(node)

        def visit_ListComp(self, node):
            self.found["comprehensions"] = True
            self.generic_visit(node)

        def visit_DictComp(self, node):
            self.found["comprehensions"] = True
            self.generic_visit(node)

        def visit_Lambda(self, node):
            self.found["lambda-functions"] = True
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            # check *args, **kwargs
            for arg in node.args.args:
                if arg.arg == "args" or arg.arg == "kwargs":
                    self.found["args-and-kwargs"] = True
            if node.args.vararg or node.args.kwarg:
                self.found["args-and-kwargs"] = True
            self.generic_visit(node)

        def visit_For(self, node):
            self.loop_depth += 1
            self.found["for loops"] = True
            if self.loop_depth >= 2:  # means we’re inside a nested for
                self.found["nested for loops"] = True
            self.generic_visit(node)
            self.loop_depth -= 1

        def visit_While(self, node):
            self.while_loop_depth += 1
            self.found["while loops"] = True

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "Invalid Python code"}
    
    visitor = StructureVisitor()
    visitor.visit(tree)
    return visitor.found
#END CODE FROM CHATGPT

def check_length_specifications(problem_type, avg_length, cur_length):
    if avg_length <= 20:
        tolerance = 6
    elif avg_length <= 50:
        tolerance = 20
    elif avg_length <= 100:
        tolerance = 30
    else:
        tolerance = int(avg_length*0.40)

    upper_bound = avg_length + tolerance
    lower_bound = avg_length - tolerance

    if problem_type == "determine_output":
        upper_bound = 25
        lower_bound = 2

    # print (f"LOWER BOUND: {lower_bound}")
    # print (f"UPPER BOUND: {upper_bound}")

    # print (f'AVG LENGTH: {avg_length}')
    # print (f'CUR LENGTH: {cur_length}')

    if cur_length > upper_bound:
        diff = cur_length - upper_bound
        return (False, diff)
    
    elif cur_length < lower_bound:
        diff = cur_length - lower_bound
        return (False, diff)

    return (True, 0)

def validate_against_user_selections(problem_type, specifications, chatgpt_text, last_attempt=False):
    #create new code string without docstrings to accurately measure num of code lines
    new_text = copy.deepcopy(chatgpt_text)
    if problem_type == "fill_in_vars":
        indices = [m.start() for m in re.finditer('\"\"\"', new_text)]
        for i in range(len(indices))[::-2]:
            start = indices[i-1]
            end = indices[i]
            new_text = new_text[:start+3] + ' ' + new_text[end:]

    #check length specs
    avg_length = int((specifications["required_length"][0] + specifications["required_length"][1])/2)
    meets_length_specs, diff = check_length_specifications(problem_type, avg_length, len(new_text.split("\n")))
    length_explanation = ""
    if not meets_length_specs:
        if diff > 0:
            length_explanation = f"This code is too long by about {diff} and needs to be shortened."
        else:
            length_explanation = f"This code is too short by about {abs(diff)} and needs to be lengthened."

    detected_structures = detect_structures(new_text[8:-3])

    should_include = []
    should_not_include = []
    for key, value in detected_structures.items():
        if value is False and key in specifications['selected_structures']:
            should_include.append(key)
        elif value is True and key in specifications['disallowed_structures']:
            should_not_include.append(key)

    info = [should_include, should_not_include, diff]
    
    structure_explanation = ""
    if should_include or should_not_include:
        structure_explanation = f"The code should contain these structures: {', '.join(specifications['selected_structures'])} and should not include {', '.join(specifications['disallowed_structures'])}. Unfortunately, there are issues."

        if should_include:
            structure_explanation += f" I need you to add these structures: {', '.join(should_include)}."
        if should_not_include:
            structure_explanation += f" I need you to remove these structures: {', '.join(should_not_include)}."

        structure_explanation += " All other structures should remain untouched."

    if length_explanation or structure_explanation:
        general_instructions = f" This block of Python code has been generated as a practice problem for a student: \n {chatgpt_text}. \n Unfortunately, there are several issues with it."
        general_instructions += length_explanation + structure_explanation
        general_instructions += "If you need to remove or add large chunks of the code to satisfy these requests, please do so. Please keep docstrings the same unless you're modifying their function, and do not count docstring lines as adding to the total length of the code. Otherwise, you can change functions and code as needed. Do not introduce the code or provide a summary of the changes, just output the modified code."

        if not length_explanation and structure_explanation:
            general_instructions += " The length of the code (not including docstrings) should be as close as possible to the original."

        #send query to anthropic saying that parameters have been violated

        if problem_type == "determine_output":
            general_instructions += " Additionally, please ask yourself: could a user figure out what the code outputs by reading through the code in their head? If they cannot, change the problem and docstrings such that the user can do this in their head."


        print ("Code did not meet specifications for the following reasons: ")
        if length_explanation:
            print (length_explanation)
        if should_include:
            print (f"Code should have included structures but did not: {should_include}")
        if should_not_include:
            print (f"Code should not have included structures but did: {should_not_include}")       

        if last_attempt:
            #use a better model if this is our last attempt
            print ("Last attempt, using better model...")
            new_code = anthropic_query(general_instructions, 0.5, "claude-3-7-sonnet-20250219")
            #new_code = anthropic_query(general_instructions, 0.5, "claude-sonnet-4")
        
        else:
            new_code = anthropic_query(general_instructions)

        return False, new_code, info

    #no issues with the code
    return True, chatgpt_text, info


def query_loop(user_selections):
    best_code = {}
    result = True

    #get query
    print ("Getting first query...")
    problem_type, query, specifications = get_query(user_selections)
    print (f"Full query: {query}")

    #send query to chatgpt for the first time
    print ("Sending query to chatgpt...")
    chatgpt_text = chatgpt_query(query)

    #initializing variables for loop
    last_attempt = False
    correct_answer = None
    attempts = 1
    print ("Starting verification loop...")
    max_attempts = 2
    while attempts <= max_attempts:

        #check for last attempt
        if attempts == max_attempts:
            last_attempt = True

        #check code against user specifications, send to anthropic if it fails to meet any
        print ("Validating code against user selections...")
        code_unmodified, chatgpt_text, info = validate_against_user_selections(problem_type, specifications, chatgpt_text, last_attempt)

        #confirm code runs and is safe
        code_is_good, correct_answer, err_msg = validate(chatgpt_text)

        #code is safe and meets all user specifications. return it as is
        if code_is_good and code_unmodified:
            print ("Code is valid, returning...")
            break

        #code is valid but does not meet user specifications
        if code_is_good:
            print ("Storing code for later use...")
            best_code = update_best_code(info, chatgpt_text, best_code, correct_answer)

        #code is not valid (did not run); ask anthropic to fix it
        else:
            print ("Exception in code, sending to anthropic for fix...")
            code_fix_query = f"There is an issue with this Python code: \n {chatgpt_text}.\n It is throwing this error: {err_msg}. Could you fix the error? Change only as much as you need to in order to fix the error. Do not add any comments or annotations to the code that do not already exist. Just reply with the code, do not introduce it or explain the fixes."
            #TODO: if last attempt, should we call the better model?
            chatgpt_text = anthropic_query(code_fix_query)
            #chatgpt_text = anthropic_query(code_fix_query, model="claude-sonnet-4")

        #increment attempts
        attempts += 1

    if attempts >= max_attempts:
        #pull best code here
        chatgpt_text, correct_answer = best_code[max(best_code)]
        #TODO: if code fails by x points or more, set to false?
        result = True
        print (f"Failed to generate code that met user specifications, best code was: {max(best_code)}")

    return result, problem_type, correct_answer, chatgpt_text


def update_best_code(info, chatgpt_text, best_code, correct_answer):
    #confidence starts at 0, and we subtract 1 for each structure that should have been included but
    #wasn't/shouldn't have been included that was. every 4 lines over/under the limit subtracts a point
    #the 'best' possible code is 0
    #the best code in the dictionary will always be its max
    should_include, should_not_include, diff = info
    confidence = 0
    confidence += -len(should_include) - len(should_not_include) - (abs(diff) // 4)

    if confidence not in best_code:
        best_code[confidence] = [chatgpt_text, correct_answer]

    else:
        #we don't care about ties, don't store this info
        pass

    return best_code

def validate_safety_and_query(request, query, temperature, problem_type) -> tuple[bool, str, str, str]:
    """Queries ChatGPT, then validates the result. Output is a tuple of the form (bool, str, str, str), which maps to
       (did query succeed, chatgpt_text response if success, error message if failure, code output).
    """
    fail_count = 0
    output = None

    #if we fail more than 3 times, return an error message to the user
    while fail_count < 3:
        chatgpt_response = chatgpt_query(query, temperature, True)

        #chatgpt error handling
        if chatgpt_response.status_code != 200:
            err_msg = chatgpt_response.text
            err_code = chatgpt_response.status_code
            err = err_msg + "code: " + err_code
            return False, "", err, ""

        #message was successful, get response data and text
        response_data = chatgpt_response.json()
        chatgpt_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        
        #store extra data about the problem in the session
        request.session["problem_text"] = chatgpt_text

        if problem_type == "fill_in_vars":
            result, output = True, ""

        else:
            result, output = validate(chatgpt_text)

        if not result:
            fail_count += 1
            continue

        return True, chatgpt_text, "", output

    if fail_count >= 3:
        err_msg = "Attempts exceeded. Please contact the administrator."
        print (err_msg)
        return False, "", err_msg, ""

    #get response from chatgpt_query. if false, update fail_count, try again. continue
    #get response data
    #create separate fn for formatting query (make sure it has backticks on either side and 'output:' is removed)
    #create counter
    #call into validate 3 times. if we fail, 


def chatgpt_query(query, temperature=0.5, raw_response=False, model="gpt-4.1-mini"):
    """Given a query and a temperature, queries ChatGPT via OpenAI SDK.
       If raw_response is True, returns the unprocessed ChatGPT response object.
       If raw_response is False, returns only the text content of the ChatGPT response.
    """

    openai.api_key = settings.SECRET_KEY

    response = openai.responses.create(
        model=model,
        input=query,
        temperature=temperature
    )

    if raw_response:
        return response

    # Extract text content exactly like your old code
    # response.output is a list of objects with 'content' lists
    # Each content item is a dict with 'type' and 'text'
    try:
        chatgpt_text = response.output[0].content[0].text
    except (IndexError, AttributeError):
        chatgpt_text = "No response"

    return chatgpt_text

def anthropic_query(query, temperature=0.5, model="claude-haiku-4-5-20251001"):
    #https://docs.anthropic.com/en/docs/about-claude/models/overview
    #https://www.anthropic.com/pricing#api
    role = "You are a computer science teacher."

    client = anthropic.Anthropic()
    client.api_key = settings.ANTHROPIC_KEY

    print ("reached1")

    message = client.messages.create(
        model=model,
        max_tokens=1000,
        temperature=temperature,
        system=role,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    }
                ]
            }
        ]
    )

    print ("reached2")

    return message.content[0].text


async def async_chatgpt_query(session, query, temperature):
    #API endpoint
    url = "https://api.openai.com/v1/chat/completions"

    #request headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SECRET_KEY}"
    }

    #data
    data = {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": query}],
        "temperature": temperature
    }

    async with session.post(url, headers=headers, json=data) as response:
        response_data = await response.json()
        return response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response")

async def async_anthropic_query(session, query, temperature):
    url = "https://api.anthropic.com/v1/messages"

    headers = {
        "x-api-key": settings.ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    data = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "temperature": temperature,
        "system": "You are a computer science teacher.",
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ]
    }

    async with session.post(url, headers=headers, json=data) as response:
        response_data = await response.json()
        try:
            return response_data["content"][0]["text"]
        except (KeyError, IndexError):
            return "Anthropic returned an unexpected response."

async def double_query(query, temperature=0.5):
    #when you run this, do result = await double_query(query)
    async with aiohttp.ClientSession() as session:
        chatgpt_task = async_chatgpt_query(session, query, temperature)
        anthropic_task = async_anthropic_query(session, query, temperature)
        result1, result2 = await asyncio.gather(chatgpt_task, anthropic_task)
        return (result1, result2)

def validate(text_query) -> tuple[bool, str]:
    """Performs safety checks, then runs the problem using exec() and stores its output."""

    #removes triple backticks, formats text_query into a string
    text_query = text_query[9:-3]

    #check for infinite loops
    ast_node = ast.parse(text_query)
    for node in ast.walk(ast_node):
        #START CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
        #END CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
            print ("infinite loop")
            err_msg = "infinite loop detected"
            return False, "", "Exception: " + err_msg

    try:        
        local_vars = {}

        f = StringIO()
        with redirect_stdout(f):
            local_vars = {}
            exec(text_query, local_vars, local_vars)
            output = f.getvalue()

        #if output is not a string, turn it into one
        if type(output) != str:
            output = str(output)

        return True, output, ""

    except Exception as exception:
        #error was found, return false
        err_msg = str(exception)
        print (f"error in code. exception: {err_msg}")
        return False, "", "Exception: " + err_msg


def lines_to_exclude(lines_list):
    #assumptions: all code wrapped in function except for code at bottom
    #start from bottom: all lines are excluded until reaching whitespace, then quit
    #def
    #class
    exclude = []
    if not lines_list[-1]:
        lines_list = lines_list[:-1]
    # if not lines_list[0]:
    #     lines_list = lines_list[1:]

    #start from the end, exclude last few lines that are always the same
    print ("START CHECK FROM END")
    idx = len(lines_list) - 1
    for item in lines_list[::-2]:
        print (item)
        if not item or item[0] == " ":
            break
        exclude.append(idx)
        idx += -1

    print ("START CHECK FROM START")
    #start from top, exclude function and class headers
    for i,item in enumerate(lines_list):
        line_no_whitespace = item.strip()
        if (line_no_whitespace[:3] == "def" or line_no_whitespace[:5] == "class") and i not in exclude:
            exclude.append(i)

    #returns indices that should be excluded
    return exclude

def mix_lines(code,exclusions=[]):
    """Given code as a string and with line breaks, shuffles each line and returns it as a string.
       Optionally takes a list of indices, which excludes them from being shuffled.
    """
    
    #split code into list
    code_lines = code.split("\n")
    
    #list of all indices
    all_indices = list(range(len(code_lines)))

    #all indices to be shuffled
    inclusions = [i for i in all_indices if i not in exclusions]

    #all lines of code to be shuffled
    inclusions_lines = [code_lines[i] for i in inclusions]

    random.shuffle(inclusions_lines)

    for i,item in enumerate(inclusions):
        #places shuffled code back into inclusions indices
        code_lines[item] = inclusions_lines[i]

    return "\n".join(code_lines)

#TODO: cache most recent unanswered problem, show that to the user first, or show in history
def store_in_db(request, current_user, problem_text, is_user_correct, problem_type, correct_code):
    """Stores a problem in the user's history if it does not already exist."""
    if request.user.is_authenticated:
        if problem_type == "determine_output":
            problem_hash = hashlib.sha256(problem_text.encode()).hexdigest()
        if problem_type == "fill_in_vars":
            problem_hash = hashlib.sha256(correct_code.encode()).hexdigest()
        elif problem_type == "drag_and_drop":
            problem_hash = hashlib.sha256(correct_code.encode()).hexdigest()
        if not UserHistory.objects.filter(user=current_user, problem_hash=problem_hash).exists() and problem_hash:
            UserHistory.objects.create(user=current_user, problem_text=problem_text, is_correct=is_user_correct, problem_type=problem_type, problem_hash=problem_hash, correct_answer=correct_code)

#START CODE FROM CHATGPT
def normalize_match(match):
    original = match.group()
    
    if '.' in original:
        num = round(float(original), 3)
        return str(num)
    
    return original  # preserve leading zeros for integers

def normalize_output_answer(answer):
    """Extracts all numbers, rounds decimals to 3 digits, preserves leading zeros for integers,
    and removes newlines."""
    normalized = re.sub(r'[-+]?\d*\.?\d+', normalize_match, answer)
    return normalized.replace('\n', '')
#END CODE FROM CHATGPT

def get_random_item_in_list(array):
    """Returns a random element in the provided array."""
    rand_int = random.randint(0,len(array)-1)
    return array[rand_int]

def get_query(user_selections):
    specifications = {}
    full_query = ""
    problem_types = ["determine_output", "fill_in_vars", "drag_and_drop",]
    problem_type = problem_types[random.randint(0, len(problem_types)-1)]

    #problem_type = "fill_in_vars"
    required_structures, disallowed_structures, specifications = process_user_selections_structures_and_difficulty(problem_type, user_selections, specifications)
    subject_request = process_user_selections_subjects(user_selections)
    required_length, specifications = process_user_selections_problem_length(problem_type, user_selections, specifications)

    must_do = "-" + "\n-".join(static_variables.instructions[problem_type]["do"]) + "\n"
    must_not_do = "-" + "\n-".join(static_variables.instructions[problem_type]["do-not"]) + "\n"

    constraints = " All of the requirements on this list must be met: \n" + must_do + required_structures + must_not_do + "-" + disallowed_structures
    full_query = static_variables.instructions["base_query"] + constraints + "\n-" + subject_request + "\n-" + required_length

    if problem_type == "determine_output":
        full_query += "For this code block in particular: nested 'for' loops must NOT be used. And ALL calculations must be doable with mental math."

    print (f"problem type: {problem_type}")
    print (f"subject: {subject_request}")
    print (f"required structures: {required_structures}")
    print (f"disallowed structures: {disallowed_structures}")

    return problem_type, full_query, specifications

def process_user_selections_subjects(user_selections):
    num_structures = 7
    allowed_domains = []
    count = 0
    
    #populates allowed_domains
    for key, value in user_selections['checkbox_states'].items():
        if count <= num_structures:
            count += 1
            continue
        if value == True:
            allowed_domains.append(key)
        count += 1
    
    #randomly picks a domain
    chosen_domain = allowed_domains[random.randint(0,len(allowed_domains)-1)]
    chosen_domain_readable = static_variables.subject_mappings[chosen_domain]

    #randomly selects a subfield within the domain
    subjects = static_variables.subfield_info[chosen_domain]["subjects"]
    chosen_subject = subjects[random.randint(0,len(subjects)-1)]

    #randomly selects a concept within the domain
    concepts = static_variables.subfield_info[chosen_domain]["concepts"] + static_variables.general_attributes["general_concepts"]
    chosen_concept = concepts[random.randint(0,len(concepts)-1)]

    #randomly selects a question type within the domain
    q_types = static_variables.subfield_info[chosen_domain]["q_types"] + static_variables.general_attributes["general_q_types"]
    chosen_q_type = q_types[random.randint(0,len(q_types)-1)]

    #turns chosen attributes into sentence

    #if length is less than 30, pick either chosen_concept or chosen_q_type.
    if int(user_selections['problem_length_slider']) < 30:
        coin_flip = random.randint(0,1)
        if coin_flip == 0:
            selection = chosen_concept
        else:
            selection = chosen_q_type
        print (f"Chosen subject: {chosen_domain_readable} related to {selection}.")
        #return f" Generate code from the domain of {chosen_domain_readable} related to {selection}."
        return f" Generate code from the domain of {chosen_subject} related to {selection}."

    print (f"Chosen subject: {chosen_domain_readable} related to {chosen_subject} involving {chosen_concept} and {chosen_q_type}.")
    return f" Generate code from the domain of {chosen_domain_readable} related to {chosen_subject} involving {chosen_concept} and {chosen_q_type}."

def check_for_no_subjects(user_selections):
    num_structures = 7

    #gets a list of truthy values in user_selections['checkbox_states']
    values = [value for key,value in user_selections['checkbox_states'].items()]
    values = values[num_structures:]
    if any(values):
        return user_selections
    
    #they are all false. flip them all to true
    count = 0
    for key, value in user_selections['checkbox_states'].items():
        if count > num_structures:
            user_selections['checkbox_states'][key] = True
        count += 1

    return user_selections

def process_user_selections_structures_and_difficulty(problem_type, user_selections, specifications):
    num_structures = 7

    allowed_structures = []
    disallowed_structures = []
    count = 0
    
    #populates allowed_structures and disallowed_structures
    for key, value in user_selections['checkbox_states'].items():
        if count > num_structures:
            break
        #formatted_key = key.replace("-", " ")
        if value == True:
            allowed_structures.append(key)
        else:
            disallowed_structures.append(key)
        count += 1

    selected_structures = []
    difficulty_level = int(user_selections['difficulty_level_slider'])
    allowed_structures_permanent = copy.deepcopy(allowed_structures)

    #if difficulty < 1 or problem type is determine_output, disallow nested for loops
    if difficulty_level < 2 or problem_type == "determine_output":
        #disallowed_structures.append('nested for loops')
        #disallowed_structures.append("for loops")
        #disallowed_structures.append("while loops")
        pass

    while difficulty_level > 0 and allowed_structures:
        chosen_index = random.randint(0,len(allowed_structures)-1)
        selected_structures.append(allowed_structures[chosen_index])
        del allowed_structures[chosen_index]
        difficulty_level += -1
    
    disallowed_structures.extend(allowed_structures)

    structure_fragment_positive = ", ".join([static_variables.structure_mappings[i] for i in selected_structures])
    structure_fragment_negative = ", ".join([static_variables.structure_mappings[i] for i in disallowed_structures])

    if not allowed_structures_permanent:
        do = ""
        do_not = f"Do not use ANY of these structures in the code: {structure_fragment_negative}."
    
    else:
        do = f"Use ALL of these structures in the code (one or more of each): {structure_fragment_positive}. Use each function piece to its fullest. For example, if using enumerate(), both the counter and the item should be used in the code. \n"
        do_not = f"Please do not use ANY of these structures in the code: {structure_fragment_negative}. \n"

    specifications["selected_structures"] = selected_structures
    specifications["disallowed_structures"] = disallowed_structures

    return do, do_not, specifications

def process_user_selections_problem_length(problem_type, user_selections, specifications):
    problem_length = int(user_selections['problem_length_slider'])
    #might want to adjust these values so the gap is relatively wider on lower lengths,
    #and relatively narrower on higher lengths (10-13 vs 120-130, for example)
    base_start = 10
    base_end = 13
    mod1 = 0.5
    mod2 = 0.6

    if problem_type == "determine_output":
        #starting length: 3-
        #ending length: 
        base_start = 2
        base_end = 4
        mod1 = 1
        mod2 = 1

    #for non determine_output type problems: 5-55
    starting_length = int(base_start*problem_length*mod1)

    #for non determine_output type problems: 7-85
    ending_length = int(base_end*problem_length*mod2)

    specifications["required_length"] = (starting_length, ending_length)

    return f" The length of the problem should be between {starting_length} and {ending_length} lines.", specifications