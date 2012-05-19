import re

patterns = [
    ['[sxz]$', '$', 'es'],
    ['[^aeioudgkprt]h$', '$', 'es'],
    ['(qu|[^aeiou])y$', 'y$', 'ies'],
    ['([^aeiou])o$', '$', 'es', 'piano,photo,kilo'],
    ['f$|fe$', '$', 's',
        'calf,half,knife,leaf,life,loaf,self,sheaf,shelf,thief,wife,wolf'],
    ['f$|fe$', 'f$|fe$', 'ves'], ['$', '$', 's']
]

unchanged = [
    'deer', 'sheep', 'swine', 'trout', 'cod', 'grouse', 'craft', 'counsel',
    'works', 'means', 'bellows', 'series', 'mews', 'species', 'barracks',
    'headquarters', 'gallows', 'kennels', 'fish', 'information', 'advice',
    'money', 'news', 'success', 'furniture', 'work', 'fruit', 'cream', 'ink',
    'clothes', 'goods', 'contents', 'sweepings', 'odds', 'greens', 'shorts',
    'trousers', 'jeans', 'scissors', 'pyjamas', 'spectacles', 'tights', 'data',
    'media', 'honey'
]

exceptions = {
    'woman': 'women',
    'ox': 'oxen',
    'louse': 'lice',
    'tooth': 'teeth',
    'goose': 'geese',
    'child': 'children',
    'foot': 'feet',
    'mouse': 'mice',
    'man': 'men'
}

class Plural:
    def rules(self):
        for pattern in patterns:
            # parse pattern
            if len(pattern) == 4:
                match, search, replace, exceptions = pattern
            else:
                match, search, replace = pattern
                exceptions = []
            if exceptions:
                exceptions = [x for x in exceptions.split(',')]

            # defining functions
            def match_rule(word):
                return re.search(match, word) and \
                    (not exceptions or word not in exceptions)

            def apply_rule(word):
                return re.sub(search, replace, word)

            # generate next rule
            yield (match_rule, apply_rule)

    def make(self, word_singular):
        word = word_singular.lower()

        # test for unliteral symbols
        if re.search('[_0-9]', word):
            word_excluded = re.sub('[_0-9]', ' ', word).strip().split(' ')[0]
            return word.replace(word_excluded, self.make(word_excluded), 1)

        # test for unchanged
        if word in unchanged:
            return word

        # test for exceptions
        for k, v in exceptions.items():
            if re.search(k + '$', word):
                return re.sub(k + '$', v, word)

        # test for rules
        for (match_rule, apply_rule) in self.rules():
            if match_rule(word):
                return apply_rule(word)
        return word
