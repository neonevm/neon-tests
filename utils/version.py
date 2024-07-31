import re


def remove_heading_chars_till_first_digit(input_string):
    result = re.sub(r'^[^\d]*', '', input_string)
    return result
