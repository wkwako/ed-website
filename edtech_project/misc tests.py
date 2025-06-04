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

code_lines = ['', 'def magnetic_change(initial_strength, steps):', '    change_rate = 0.02', '    current_strength = initial_strength', '    for i in range(steps):', '        current_strength += current_strength * change_rate', '    return round(current_strength, 2)', '', 'result = magnetic_change(100, 4)', 'output = f"Strength: {result}"', 'print(output)', '']

exclusions = lines_to_exclude(code_lines)
print (exclusions)


def simulate_api_response():
    response_times = [120, 200, 150, 100, 180]
    results = [x * 0.5 for x in response_times]
    return results
def get_minimum(values):
    min_value = values[0]
    for i in range(1, len(values)):
        if values[i] < min_value:
            min_value = values[i]
    return min_value
def calculate_average(test_cases):
    total = sum(test_cases)
    return total / len(test_cases)
response_data = simulate_api_response()
minimum_response = get_minimum(response_data)
average_response = calculate_average(response_data)
output = f"Min: {minimum_response}, Avg: {average_response}"
print(output)