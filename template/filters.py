from tornado.escape import xhtml_escape

from ..helpers.strings import trim as string_trim


class TemplateFilter(object):
    autoescape = True

    def __ror__(self, string):
        return self.transform(string)

    def __call__(self, *args, **kwargs):
        self.__init__(*args, **kwargs)
        return self


class Escape(TemplateFilter):
    def __init__(self, escaper=xhtml_escape):
        self.escaper = escaper

    def transform(self, string):
        return self.escaper(string)

escape = Escape()


class LineBreaks(TemplateFilter):
    def __init__(self, breaker='<br />', escape_source=escape):
        self.breaker = breaker
        self.escape_source = escape_source

    def transform(self, string):
        string = string | self.escape_source if self.escape_source else string
        return string.replace('\n', self.breaker)

linebreaks = LineBreaks()


class Trim(TemplateFilter):
    def __init__(self, char=' ', replace='', repeat=2):
        self.char = char
        self.replace = replace
        self.repeat = repeat

    def transform(self, string):
        return string_trim(string, self.char, self.replace, self.repeat)

trim = Trim()

