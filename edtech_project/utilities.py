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
import anthropic
import copy
from . import static_variables

#START CODE FROM CHATGPT
def detect_structures(code: str):
    class StructureVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found = {
                "enumerate": False,
                "zip": False,
                "any_all": False,
                "map_filter": False,
                "set_ops": False,
                "data_slicing": False,
                "conditional_chain": False,
                "list_dict_comprehensions": False,
                "lambda": False,
                "args_kwargs": False,
                "double_nested_for": False,
            }
            self.loop_depth = 0

        def visit_Call(self, node):
            # enumerate
            if isinstance(node.func, ast.Name) and node.func.id == "enumerate":
                self.found["enumerate"] = True
            # zip
            if isinstance(node.func, ast.Name) and node.func.id == "zip":
                self.found["zip"] = True
            # any/all
            if isinstance(node.func, ast.Name) and node.func.id in {"any", "all"}:
                self.found["any_all"] = True
            # map/filter
            if isinstance(node.func, ast.Name) and node.func.id in {"map", "filter"}:
                self.found["map_filter"] = True
            self.generic_visit(node)

        def visit_BinOp(self, node):
            # set operations: union |, intersection &, difference -, symmetric difference ^
            if isinstance(node.op, (ast.BitOr, ast.BitAnd, ast.Sub, ast.BitXor)):
                if isinstance(node.left, ast.Set) or isinstance(node.right, ast.Set):
                    self.found["set_ops"] = True
            self.generic_visit(node)

        def visit_Subscript(self, node):
            # data slicing (e.g., a[1:3])
            if isinstance(node.slice, ast.Slice):
                self.found["data_slicing"] = True
            self.generic_visit(node)

        def visit_If(self, node):
            # conditional chaining: if ... elif ...
            if any(isinstance(orelse, ast.If) for orelse in node.orelse):
                self.found["conditional_chain"] = True
            self.generic_visit(node)

        def visit_ListComp(self, node):
            self.found["list_dict_comprehensions"] = True
            self.generic_visit(node)

        def visit_DictComp(self, node):
            self.found["list_dict_comprehensions"] = True
            self.generic_visit(node)

        def visit_Lambda(self, node):
            self.found["lambda"] = True
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            # check *args, **kwargs
            for arg in node.args.args:
                if arg.arg == "args" or arg.arg == "kwargs":
                    self.found["args_kwargs"] = True
            if node.args.vararg or node.args.kwarg:
                self.found["args_kwargs"] = True
            self.generic_visit(node)

        def visit_For(self, node):
            self.loop_depth += 1
            if self.loop_depth >= 2:  # means we’re inside a nested for
                self.found["double_nested_for"] = True
            self.generic_visit(node)
            self.loop_depth -= 1

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"error": "Invalid Python code"}
    
    visitor = StructureVisitor()
    visitor.visit(tree)
    return visitor.found
#END CODE FROM CHATGPT

def get_length_specifications(avg_length, cur_length):
    if avg_length <= 20:
        tolerance = 10
    elif avg_length <= 50:
        tolerance = 30
    elif avg_length <= 100:
        tolerance = 40
    else:
        tolerance = int(avg_length*0.40)

    upper_bound = avg_length + tolerance

    if cur_length > upper_bound:
        diff = cur_length - upper_bound
        return (False, diff)

    return (True, 0)

def validate_against_user_selections(problem_type, specifications, chatgpt_text):
    #create new variable new_text, which holds chatgpt without docstrings
    length_explanation = ""
    general_explanation = ""
    meets_selected_structures_specs = True
    meets_disallowed_structures_specs = True

    new_text = copy.deepcopy(chatgpt_text)
    if problem_type == "fill_in_vars":
        indices = [m.start() for m in re.finditer('\"\"\"', new_text)]
        for i in range(len(indices))[::-2]:
            start = indices[i-1]
            end = indices[i]
            new_text = new_text[:start+3] + ' ' + new_text[end:]
        
    avg_length = int(specifications["required_length"][0]/specifications["required_length"][1])
    
    
    #check length specs
    meets_length_specs, too_long_count = get_length_specifications(avg_length, len(new_text.split("\n")))
    if not meets_length_specs:
        lenth_explanation = f"This code is too long by about {too_long_count} and needs to be shortened. If you need to take out functions to meet length requirements, that's okay. The code must still meet the following requirements:"

    #define class here with ast, check for structures
    structures_found = detect_structures(new_text[8:-3])
    print (f"STRUCTURES FOUND: {structures_found}")
    print (f"")
    #may not be tracking conditional chains

    #if any element in selected_structures is False, flag it
    #if any element in disallowed_structures is True, flag it
    for keys, value in structures_found.items():

        pass

    #send query to anthropic saying that parameters have been violated
    #give original prompt, code, and the issues with it, and ask it to generate a new block of code

    #check selected_structures

    #check disallowed_structures


    pass

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
            result, output = validate(chatgpt_text, problem_type)

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


def chatgpt_query(query, temperature, raw_response=False, model="gpt-4.1-mini"):
    """Given a query and a temperature, queries ChatGPT. If raw_response is True,
       returns the unprocessed ChatGPT response. If raw_request is False, returns
       only the text content of the ChatGPT response.
    """
    #API endpoint
    url = "https://api.openai.com/v1/chat/completions"

    #request headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SECRET_KEY}"
    }

    #data
    data = {
        "model": model,
        "messages": [{"role": "user", "content": query}],
        "temperature": temperature
    }

    #does the API request
    chatgpt_response = requests.post(url, headers=headers, json=data)
    
    if not raw_response:
        response_data = chatgpt_response.json()
        chatgpt_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "No response")
        return chatgpt_text

    return chatgpt_response

def anthropic_query(query, temperature=0.5, model="claude-3-5-haiku-20241022"):
    #https://docs.anthropic.com/en/docs/about-claude/models/overview
    #https://www.anthropic.com/pricing#api
    role = "You are a computer science teacher."

    client = anthropic.Anthropic()
    client.api_key = settings.ANTHROPIC_KEY

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
        "model": "claude-3-5-haiku-20241022",
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

def validate(text_query,problem_type) -> tuple[bool, str]:
    """Runs the ChatGPT-generated problem to retrieve its output. Performs safety checks."""

    #removes triple backticks, formats text_query into a string
    text_query = text_query[9:-3]

    #check for infinite loops
    ast_node = ast.parse(text_query)
    for node in ast.walk(ast_node):
        #START CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
        #END CODE FROM 'python_user' on stackoverflow: https://stackoverflow.com/questions/67230018/python-checking-its-own-code-before-running-usage-errors
            print ("infinite loop")
            return False, ""

    try:        
        local_vars = {}

        #we trust the input and users don't have access to query chatgpt, this is safe
        exec(text_query, local_vars, local_vars)

        output = local_vars['output']

        #if output is not a string, turn it into one
        if type(output) != str:
            output = str(output)

        return True, output

    except Exception as exception:
        #error was found, return false
        err_msg = str(exception)
        print (f"error in code. exception: {err_msg}")
        return False, ""


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


#TODO: this if statement could be made more efficient by hashing/indexing the code so we aren't text matching
#the whole thing
#TODO: cache most recent unanswered problem, show that to the user first, or show in history
def store_in_db(request, current_user, difficulty, problem_text, is_user_correct, problem_type, correct_code):
    """Stores a problem in the user's history if it does not already exist."""
    if request.user.is_authenticated:
        if problem_type == "determine_output":
            problem_hash = hashlib.sha256(problem_text.encode()).hexdigest()
        if problem_type == "fill_in_vars":
            problem_hash = hashlib.sha256(correct_code.encode()).hexdigest()
        elif problem_type == "drag_and_drop":
            problem_hash = hashlib.sha256(correct_code.encode()).hexdigest()
        if not UserHistory.objects.filter(user=current_user, problem_hash=problem_hash).exists() and problem_hash:
            UserHistory.objects.create(user=current_user, problem_text=problem_text, difficulty=difficulty, is_correct=is_user_correct, problem_type=problem_type, problem_hash=problem_hash, correct_answer=correct_code)

#START CODE FROM CHATGPT
def normalize_match(match):
    num = float(match.group())  
    num = round(num, 3)         
    return str(int(num)) if num.is_integer() else str(num)

def normalize_output_answer(answer):
    """Given a string, extracts all numbers and rounds them to 3 digits, then places them back in the string."""
    return re.sub(r'[-+]?\d*\.?\d+', normalize_match, answer)
#END CODE FROM CHATGPT

def get_random_item_in_list(array):
    """Returns a random element in the provided array."""
    rand_int = random.randint(0,len(array)-1)
    return array[rand_int]

def query_determine_output(difficultyLevel):
    """Creates the query for the 'determine_output' problem type."""
    query = 'I\'d like you to generate a snippet of Python code for me. The purpose of the code is educational, so it should give students practice reading code. Here are the general specifications: The code must not have any annotations or comments. Variable and function names must make sense (be something a human would write). The code should do something that would be useful to a human. Please use i, j, and k for iterators in for loops. At the end of the code, there should be a line that causes it to output a number or phrase (a student should be able to type its output into a text box for practicing purposes). The output should be limited to 15 characters or fewer, and not more than one line long. It should not be obvious what the code is doing, but it should be decipherable after looking at it for a few minutes. If using for loops, the number of iterations through the most nested for loop should never be more than 5. Please store the output of the code in a variable called \'output\', where the last line prints the output variable. Do not include descriptions of the code. Do not use input() or random() functions in the code.'

    subject_query = select_subject("determine_output")
    print (f"subject: {subject_query}")
    query += subject_query

    #prevent common problems
    if random.randint(1,10) != 10:
        restrict_common_queries = " If this subject could feasibly use an example involving dna sequencing, calculating the mean/average, factorials, or population growth, do not make those the main part of the problem."
        query += restrict_common_queries
    
    #add some random variance
    if random.randint(1,10) > 5:
        adjective_list = "a little,moderately,fairly,sort of,kind of,a bit,a tiny bit,somewhat".split(",")
        tricky_level = f" Make this problem {get_random_item_in_list(adjective_list)} tricky."
        query += tricky_level
    
    if difficultyLevel == "Easy":
        query += ' The code must be between 5 and 10 lines long. Do not use more than one \'for\' loop. Do not use list/dictionary comprehensions. '

    elif difficultyLevel == "Medium":
        query += ' The code must be between 15 and 30 lines long. Please use list comprehensions in place of single-nested \'for\' loops, where applicable.'

    elif difficultyLevel == "Hard":
        query += ' The code must be between 50 and 100 lines long. Please use list comprehensions and dictionary comprehensions in place of single-nested forloops, where applicable. '

    #TODO: if still seeing lack of variety, ask ChatGPT to randomize the code at the end.
    #randomizer = random.randint(1,3)
    #query += f"I would also like you to slightly randomize the code. Create the code again with the same constraints, but with small differences. These differences may impact variable names, function names, and the output. Perform this randomization {randomizer} times, and only return the final code block. Do not introduce the code with descriptions, do not show any code other than the final randomized code. "

    #enforce important restrictions variable.
    query += "Again, \'for\' loops should no more than 5 iterations. Do not use nested \'for\' loops. Lists cannot have more than 5 elements. The output cannot be a dictionary or a set. Please store the output of the code in a variable called \'output\'. The last line of the code must be print(output), with normal closing grave marks."

    return query

def query_fill_in_vars(difficultyLevel):
    """Creates the query for the 'fill_in_vars' problem type."""
    #query = 'I\'d like you to generate a snippet of Python code for me. The purpose of the code is educational, so it should give students practice reading code. Here are the general specifications: The code must not have any annotations, comments, or docstrings. Variable and function names must make sense (be something a human would write). The code should do something that would be useful to a human. Please use i, j, and k for iterators in for loops. At the end of the code, there should be a line that causes it to output a number or phrase (a student should be able to type its output into a text box for practicing purposes). The output should be limited to 50 characters or fewer, and not more than one line long. Please store the output of the code in a variable called \'output\', where the last line prints the output variable. Do not include descriptions of the code.'

    query = 'I\'d like you to generate a snippet of Python code for me. The purpose of the code is educational, so it should give students practice reading code. Here are the general specifications: The code must not have any comments or annotations, but it should have docstrings following the PEP8 python styling conventions. Write one docstring for each function and class that contains a short summary, descriptions of parameters, and the function return value (if applicable). Use \"Args\" and \"Returns\" for this. Do not write docstrings for __init__() functions. Variable and function names must make sense (be something a human would write). The code should do something that would be useful to a human. Please use i, j, and k for iterators in for loops. All code must be wrapped in a function or a class.  Do not include descriptions of, or introductions to, the code; just respond with the code.'


    #prevent common problems
    if random.randint(1,10) != 10:
        restrict_common_queries = " If this subject could feasibly use an example involving dna sequencing, calculating the mean/average, factorials, or population growth, do not make those the main part of the problem."
        query += restrict_common_queries
    
    #add some random variance
    adjective_list = "a little,moderately,fairly,sort of,kind of,a bit,a tiny bit,somewhat".split(",")
    tricky_level = f" Make this problem {get_random_item_in_list(adjective_list)} tricky."
    query += tricky_level

    #enforce 'output' variable.
    #query += " Please store the output of the code in a variable called \'output\'. The last line of the code must be print(output), with normal closing grave marks. Do not write a function on a line by itself, all function calls must be placed in variables."

    #all code must be in a function, otherwise there's nothing for the user to do
    #query += " Other than this line, all code must be wrapped in one or more functions. Do not use any wrapper functions. Place test calls to the function at the bottom of the script, before the output variable."

    #easy vs medium/hard problems have different subjects
    easy_subjects = "checking if a number (1-10) is divisible by another,listing all divisors of a number,counting the number of divisors,finding the largest or smallest divisor of a number,checking if a number is prime (brute force),listing the first n prime numbers,finding the smallest prime greater than a give number,something involving prime numbers,computing the gcd of a number,computing the lcm using the gcd,checking if two numbers are co-prime,basic modular arithmetic,finding the remainder of a large number,checking if a number is congruent to another modulo n,checking if a number is even or odd,counting the number of even or odd numbers in a range,summing only the even or odd numbers in a list,computing the sum of the digits in a number,finding the digital root,fibonacci sequence,converting a number from decimal to binary,converting a number from binary to decimal,checking if a number is a palindrome,something involving palindromes but not checking them,computing the first n fibonacci numbers,finding the sum of the first n fibonacci numbers,checking if a number if a fibonacci number".split(",")
    intermediate_subjects = "more complicted modular arithmetic,finding the modular inverse of a number (if it exists),checking if a number has modular inverse,finding the prime factorization of a number,counting the number of distinct prime factors,checking if a number is a product of exactly two primes,checking if a number is a product of exactly n primes (1-5),computing the sum of divisors of a number,checking if a number if perfect,checking if a number is deficient, checking if a number is abundant,something involving perfect numbers,something involving deficient numbers,something involving abundant numbers,converting a number between arbitrary bases,checking if a number is prime in a different base,computing fibonacci numbers using matrix exponentiation,finding the nth term of a gernalized recurrence relation,computing the sum of fibonacci numbers in a given range efficiently,checking if a linear equation has integer solutions,generating all primes up to n efficiently,finding the number of primes in a given range,finding the smallest power of a number that is divisible by a given number,finding the continued fraction representation of a rational number".split(",")

    #old code: Additionally, pick two variables at random and call them "unknown1" or something similar. Do not pick variables that simply rename other variables, or are just temporary variables.
    if difficultyLevel == "Easy":
        #subjects = easy_subjects
        query += ' The code must be between 10 and 15 lines long. Do not use more than one \'for\' loop. Do not use list/dictionary comprehensions.'

    elif difficultyLevel == "Medium":
        #subjects = intermediate_subjects
        query += ' The code must be between 20 and 45 lines long and contain at least 2 functions. Please use list comprehensions in place of single-nested forloops, where applicable. All function names must be called "mystery1", or something similar, so students will not know what they do from name alone.'

    elif difficultyLevel == "Hard":
        #subjects = easy_subjects + intermediate_subjects
        mod_list = ["and contain one very long function",
                    "and contain at least two functions, both moderately long",
                    "and contain at least three functions"]
        mod = mod_list[random.randint(0,len(mod_list)-1)]
        print (mod)
        query += f' The code must be between 50 and 100 lines long {mod}. Make the code more complicated if needed to reach 50 lines. Make this example moderately tricky. Please use list comprehensions and dictionary comprehensions in place of single-nested forloops, where applicable. All function names must be called "mystery1", or something similar, so students will not know what they do from name alone.'

    query += select_subject("determine_output", 50, 25, 25)

    # chosen_subject = subjects[random.randint(0,len(subjects)-1)]
    # query += f" Please use an example related to {chosen_subject}. Feel free to make a more granular problem if applicable."


    #query += " Please store the output of the code in a variable called \'output\'. The last line of the code must be print(output), with normal closing grave marks."

    #query += " Other than this line, all code must be wrapped in one or more functions."

    return query

def get_query(user_selections):
    specifications = {}
    full_query = ""
    problem_types = ["determine_output", "fill_in_vars", "drag_and_drop",]
    problem_type = problem_types[random.randint(0, len(problem_types)-1)]

    problem_type = "fill_in_vars"
    required_structures, disallowed_structures, specifications = process_user_selections_structures_and_difficulty(problem_type, user_selections, specifications)
    subject_request = process_user_selections_subjects(user_selections)
    required_length, specifications = process_user_selections_problem_length(user_selections, specifications)

    if problem_type in ["determine_output", "drag_and_drop"]:
        must_do = "-" + "\n-".join(static_variables.instructions["code_mode_output"]["do"]) + "\n"
        must_not_do = "-" + "\n-".join(static_variables.instructions["code_mode_output"]["do-not"]) + "\n"
    elif problem_type in ["fill_in_vars"]:
        must_do = "-" + "\n-".join(static_variables.instructions["code_mode_completion"]["do"]) + "\n"
        must_not_do = "-" + "\n-".join(static_variables.instructions["code_mode_completion"]["do-not"]) + "\n"

    constraints = " All of the requirements on this list must be met: \n" + must_do + required_structures + must_not_do + "-" + disallowed_structures
    full_query = static_variables.instructions["base_query"] + constraints + "\n-" + subject_request + "\n-" + required_length

    print (f"problem type: {problem_type}")
    print (f"subject: {subject_request}")
    print (f"problem length: {required_length}")
    print (f"required structures: {required_structures}")
    print (f"disallowed structures: {disallowed_structures}")

    return problem_type, full_query, specifications



def get_query_old(difficultyLevel) -> tuple[str, str]:
    """Given the difficultyLevel, randomizes the kind of problem received and returns its query.
       Returns a tuple[str,str], where the first string is the problem type and the second is the query."""
    problem_int = random.randint(2,2) #determines which problems will be generated
    problem_type = ""
    query = ""

    #subject, constraints = process_user_selections(user_selections)

    if problem_int == 1:
        problem_type = "determine_output" #standard problem
        query = query_determine_output(difficultyLevel)
    elif problem_int == 2:
        problem_type = "fill_in_vars" #text is editable, rename function/variable names
        query = query_fill_in_vars(difficultyLevel)
    elif problem_int == 3:
        problem_type = "drag_and_drop" #re-arrange lines of code
        query = query_determine_output(difficultyLevel)
    elif problem_int == 4:
        problem_type = "fix_incorrect_code" #correct errors in code

    return problem_type, query

def process_user_selections_subjects(user_selections):
    num_structures = 9
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
        return f" Generate code from the domain of {chosen_domain_readable} related to {chosen_subject}."

    return f" Generate code from the domain of {chosen_domain_readable} related to {chosen_subject} involving {chosen_concept} and {chosen_q_type}."

def process_user_selections_structures_and_difficulty(problem_type, user_selections, specifications):
    #TODO: create a function that validates that what is returned matches these specifications
    num_structures = 9

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

    print ("ATTEMPTING TO APPEND FOR LOOPS TO DISALLOWED STRUCTURES")
    print (difficulty_level, type(difficulty_level))
    print (disallowed_structures, type(disallowed_structures))
    print (problem_type, type(problem_type))

    #if difficulty < 1 or problem type is determine_output, disallow nested for loops
    if difficulty_level < 2 or problem_type == "determine_output":
        disallowed_structures.append("nested 'for' loops")

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

def process_user_selections_problem_length(user_selections, specifications):
    problem_length = int(user_selections['problem_length_slider'])
    #might want to adjust these values so the gap is relatively wider on lower lengths,
    #and relatively narrower on higher lengths (10-13 vs 120-130, for example)
    base_start = 10
    base_end = 13
    mod1 = 0.95
    mod2 = 1.05
    starting_length = int(base_start*problem_length*mod1)
    ending_length = int(base_end*problem_length*mod2)

    specifications["required_length"] = (starting_length, ending_length)

    return f" The length of the problem should be between {starting_length} and {ending_length} lines.", specifications
    
# def select_domain(CS_chance,math_chance,science_chance):
#     """Selects the domain of CS, math, and science, provided probabilities.
#        science_chance is purposefully not used and is for visibility only."""
    
#     CS_norm = 100-CS_chance
#     choice = random.randint(1,100)
#     if choice > CS_norm:
#         return "computer science"
    
#     math_norm = CS_norm - math_chance
#     if choice > math_norm:
#         return "math"
    
#     science_domains = "physics,chemistry,biology,geoscience".split(",")
#     return science_domains[random.randint(0,len(science_domains)-1)]

# def select_subject(problem_type, CS_chance=75, math_chance=15, science_chance=10):
#     """Randomly selects a domain, question type, subject, and concept, then inserts it into the query.
#        Using this method, we can produce a large number of problems with a low chance for repeats."""
#     domain = select_domain(CS_chance, math_chance, science_chance)
#     #data_structures = "1D arrays,2D arrays,dictionaries,simple class,loops conditions and arithmetic,sets,counters and flags,tuples,simulated graphs".split(",")
    
#     #START LIST FROM CHATGPT"
#     q_types = """simulating N (2-4) steps
#                  checking conditions
#                  extracting a minimum
#                  extracting a maximum
#                  counting the number of changes
#                  computing a final result
#                  tracking a state change with a variables
#                  counting how often something happens
#                  finding the first time a condition is true
#                  simulating back-and-forth motion
#                  computing how long until a threshold is reached
#                  using boolean logic to evaluate a rule set
#                  reversing a process and checking results
#                  categorizing outcomes into bins
#                  modeling a chain reaction
#                  tracking maximum distance from origin
#                  tracking whether or not a rule has been broken
#                  detecting steady-state/stabilization
#                  finding peaks or valleys
#                  tagging items based on rank or threshold""".split("\n")
#     #END LIST FROM CHATGPT"

#     if problem_type == "fill_in_vars":
#         #START LIST FROM CHATGPT
#         subjects = """strings
#                       lists
#                       dictionaries
#                       numbers
#                       basic algorithms
#                       loops and conditions
#                       math operations""".split("\n")
        
#         concepts = """reversing values
#                       counting specific elements
#                       checking conditions
#                       removing duplicates
#                       flattening nested structures
#                       finding max or min values
#                       searching for a target
#                       grouping items
#                       formatting strings
#                       accumulating sums or products
#                       comparing values
#                       converting between types
#                       validating input formats
#                       extracting patterns of substrings
#                       sorting data
#                       working with indices or positions
#                       GCD or LCD
#                       """.split("\n")
        
#         q_types += """checking conditions on each element
#                       filtering a collection based on rules
#                       transforming each element in a collection
#                       accumulating a result cross a loop
#                       validating properties of an input
#                       reordering or sorting values
#                       reformatting a string or number
#                       traversing nested structures
#                       searching for a target match
#                       extracting or slicing part of a value
#                       converting between representations
#                       removing or replacing parts of data
#                       tracking a running total or count
#                       checking for uniqueness or duplicates
#                       counting specific patterns or types
#                       computing a simple numeric property
#                       """.split("\n")
#         #END LIST FROM CHATGPT
        
#     else:
#         if domain == "physics":
#             #START LIST FROM CHATGPT"
#             subjects="""mechanics
#                         electromagnetism
#                         lenses
#                         waves
#                         kinematics
#                         cosmology
#                         fluid dynamics
#                         special relativity
#                         general relativity
#                         basic doppler effect shifts
#                         heat diffusion in 1D
#                         bouncing ball height after 1-3 bounces
#                         time delay due to signal travel
#                         refraction through 1-3 different materials
#                         basic lens magnification effects
#                         basic projectile motion (no trig)
#                         change in kinetic energy
#                         pendulum swings without damping
#                         water level change from faucet
#                         change in mass
#                         gravity effects""".split("\n")

#             concepts = """position updates over time
#                         simple force-based movement
#                         energy transfer
#                         light reflection
#                         temperature changes
#                         charge buildup
#                         friction forces
#                         elastic object collisions
#                         inelastic object collisions
#                         object collisions
#                         velocity estimation
#                         time estimation
#                         gravitational attraction
#                         net force from multiple sources
#                         orbit approximations without calculus
#                         decay simulation""".split('\n')
#             #END LIST FROM CHATGPT"

#         if domain == "chemistry":
#             #START LIST FROM CHATGPT"
#             subjects = """stoichiometry
#                         chemical reactions
#                         periodic trends
#                         atomic structure
#                         bonding
#                         acids
#                         bases
#                         oxidation and reduction
#                         chemical kinetics
#                         thermochemistry
#                         gas laws
#                         solution chemistry
#                         nuclear chemistry
#                         molecular geometry
#                         reaction equilibrium
#                         phase changes""".split("\n")
            
#             concepts = """balancing elements across reactions and products
#                         simulating concentration changes over time
#                         converting grams to moles or vice versa
#                         identifying limiting reagents
#                         calculating percent yield
#                         simulating ph changes in titrations
#                         tracking energy released
#                         tracking energy absorbed
#                         determining reaction rate based on time steps
#                         simulating half-life decay
#                         modeling temperature and pressure effects on volume
#                         assigning electron configurations
#                         sorting elements by some attribute (atomic radius, etc.)
#                         predicting solubility using polarity
#                         modeling phase transitions
#                         simulating catalyse effects based on yield
#                         estimating number of ions dissolved in solution""".split("\n")
#             #END LIST FROM CHATGPT"

#         if domain == "biology":
#             #START LIST FROM CHATGPT"
#             subjects = """cell biology
#                         genetics
#                         ecology
#                         human anatomy
#                         physiology
#                         microbiology
#                         zoology
#                         botany
#                         neuroscience
#                         evolutionary biology
#                         immunology
#                         bioinformatics""".split("\n")
            
#             concepts = """tracking population growth over time
#                         simulating predator-prey interactions
#                         gene expression based on input traits
#                         counting mutations in DNA sequences
#                         analyze trait inheritance
#                         simulating diffusion across a membrane
#                         tracking disease spread throughout a population
#                         modeling neuron firing thresholds
#                         following enzymic reactions
#                         simulating resource competition
#                         tracking food web changes
#                         modeling changes in biodiversity over time
#                         updating fitness levels based on environment
#                         simulating photosynthesis under different conditions
#                         analyze heart rate
#                         modeling immune response to infection""".split("\n")
#             #END LIST FROM CHATGPT"

#         if domain == "geoscience":
#             #START LIST FROM CHATGPT"
#             subjects = """plate tectonics
#                         seismology
#                         volcanology
#                         ocean currents
#                         weather patterns
#                         climate change
#                         layers of the earth
#                         rock cycles
#                         soil formation
#                         erosion and deposition
#                         earth's magnetic field
#                         greenhouse gases
#                         atmospheric pressure
#                         cloud formation
#                         water cycle
#                         solar radiation
#                         the seasons""".split("\n")
            
#             concepts = """tracking a gradual change in a physical property
#                         simulating an environmental process over several steps
#                         updating a value based on its interactions with its neighbors
#                         computing how a variable changes over time or space
#                         checking if conditions match a known pattern
#                         identifying significant points in a range
#                         flagging outliers or abnormal readings""".split("\n")
#             #END LIST FROM CHATGPT"

#         if domain == "computer science":
#             #START LIST FROM CHATGPT"
#             subjects = """data structures
#                         sorting data
#                         searching through data
#                         string manipulation
#                         recursion
#                         basic algorithms
#                         memory simulation
#                         bitwise operations
#                         encoding
#                         decoding
#                         simulation of logic gates
#                         graph traversal (non-heavy, simple DFS/BFS)
#                         binary trees
#                         heaps
#                         hashing
#                         collisions
#                         finite state machines
#                         basic compilers
#                         basic interpreters
#                         virtual machines (simplified)
#                         CPU scheduling
#                         stack simulation
#                         queue simulation
#                         instruction sets
#                         memory layout
#                         REST API design basics
#                         request handling and routing
#                         JSON data parsing
#                         user authentication logic
#                         session/token simulation
#                         form submission processing
#                         CRUD operations (create, read, update, delete)
#                         input validation and sanitization
#                         pagination and search filtering
#                         error logging and handling
#                         configuration loading (e.g. from JSON and ENV dicts)
#                         rate limiting simulation
#                         basic job queue simulation
#                         email/message formatting
#                         file upload simulation
#                         time-based job simulation (e.g. cron-like behavior)
#                         simple database query emulation (no SQL)
#                         microservice communication (mocked with dicts/function)
#                         simulated cloud storage or blob access
#                         basic analytics pipeline (e.g. log -> stats)
#                         API design
#                         frontend-backend communication
#                         database querying
#                         data serialization
#                         DevOps and deployment
#                         networking
#                         rate limiting
#                         code linting and formatting
#                         cloud storage interactions
#                         package management""".split("\n")
            
#             concepts = """simulating execution over multiple steps
#                         updating states
#                         tracking resource usage over time
#                         checking consistency of a system
#                         validating a system
#                         counting the number of operations of a system
#                         comparing two outputs for correctness
#                         evaluating logic conditions
#                         classifying inputs
#                         checking if a pattern exists in another
#                         finding the most used memory/register/element
#                         summarizing the final state of a system
#                         tracking growth of a structure
#                         measuring depth, size, or height of a system
#                         flagging special or end cases
#                         computing differences between two configurations
#                         identifying when a system reaches a halting condition
#                         determining whether a structure satisfies constraints
#                         extracing fields from JSON/dictionaries
#                         transforming or formatting structured data
#                         merging or splitting structured inputs
#                         handling missing or malformed data
#                         simulating login/logout flow
#                         checking if session/token is vlid
#                         validating user inputs against criteria (without using input())
#                         counting user interactions
#                         returning appropriate HTTP-like codes based on input
#                         simulating an API request and response cycle
#                         checking if input follows schema (without using input())
#                         verifying if request contains required fields
#                         simulating API unit test behavior
#                         resolving data conflicts""".split("\n")
            
#             q_types += """formatting structured data
#                         identifying missing fields
#                         simulating an API response
#                         filtering logs or entries
#                         retrying failed operations
#                         handling state transitions
#                         processing a batch of inputs (without input())
#                         simulating a cache hit/miss
#                         validating constraints
#                         checking configuration values
#                         parsing a data structure
#                         generating example output
#                         detecting common user errors""".split("\n")
#             #END LIST FROM CHATGPT"

#         if domain == "math":
#             #START LIST FROM CHATGPT"
#             subjects = """divisibility
#                         prime numbers
#                         modular arithmetic
#                         factors and multiples
#                         number classification
#                         integer sequences
#                         digital operations
#                         continued fractions
#                         patterns in number lists
#                         integer partitions
#                         modular inverse
#                         factorization
#                         congruence
#                         totatives (simple)
#                         happy numbers, squre, cube, magic, triangular, or armstrong numbers (select one)
#                         repeated digit patterns
#                         arithmetic sequences
#                         geometric sequences
#                         """.split("\n")
            
#             concepts = """checking if a number is divisible by another
#                         counting how many numbers in a list meet a condition
#                         checking if a number is prime
#                         listing the divisors of a number
#                         computing the GCD
#                         computing the LCM
#                         testing for co-prime status
#                         summing the digits of a number
#                         finding the digital root
#                         generating the first N prime numbers
#                         generating the first N Fibonacci numbers
#                         checking if a number is a Fibonacci number
#                         reversing the digits of a number
#                         checking if a number is a palindrome
#                         computing a modular inverse
#                         summing even numbers in a range
#                         summing odd numbers in a range
#                         checking palindromicity
#                         classifying a number as perfect, deficient, or abundant
#                         checking if a number is a product of exact N primes
#                         finding the smallest divisor
#                         finding the largest divisor
#                         finding the nth term of a simple recurrence""".split("\n")
            
#             q_types += """checking numerical conditions
#                         counting values with a property
#                         tracking running totals or sequences
#                         computing a transformation
#                         detecting a classification
#                         generating structured input
#                         looping through a mathematical range
#                         pattern detection or repetition
#                         building up from a recurrence
#                         checking equivalence across representations
#                         grouping or filtering by criteria""".split("\n")
#             #END LIST FROM CHATGPT"

#     chosen_subject = subjects[random.randint(0,len(subjects)-1)].strip()
#     chosen_concept=concepts[random.randint(0,len(concepts)-1)].strip()
#     chosen_q_type = q_types[random.randint(0,len(q_types)-1)].strip()

#     #combines randomly chosen domains, subjects, concepts, and question types into a string for insertion
#     #into query.
#     #START CODE FROM CHATGPT
#     query = f" Use an example from {domain} related to {chosen_subject} involving {chosen_concept} and {chosen_q_type}."
#     #END CODE FROM CHATGPT

#     return query
    