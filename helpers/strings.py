import re

def capfirst(string):
    return string[0].upper() + string[1:]

def lowfirst(string):
    return string[0].lower() + string[1:]

def trim(string, char=' ', repeat=2):
    return re.sub(char + '{%d,}' % repeat, char, string.strip(char))