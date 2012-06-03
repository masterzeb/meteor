import re

def capfirst(string):
    return string[0].upper() + string[1:]

def lowfirst(string):
    return string[0].lower() + string[1:]

def trim(string, char=' ', replace=None, repeat=2):
    replace = replace if replace is not None else char
    return re.sub(char + '{%d,}' % repeat, replace, string.strip(char))