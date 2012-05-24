# TODO: rewrite Field class. Make it descriptor with type saving,
# TODO: Field must working with validators
# TODO: no data except type and index don't stored in Field


class Field(object):
    def __init__(self, caption, required=True):
        self.caption = caption
        self.required = required

    def validate_type(self, val):
        return isinstance(val, self._type)


class StringField(Field):
    type_ = str

    def __init__(self, caption, required=True, max_length=None):
        super(StringField, self).__init__(caption, required)
        self.max_length = max_length

class IntegerField(Field):
    type_ = int

    def __init__(self, caption, required=True, rng=None):
        super(IntegerField, self).__init__(caption, required)
        self.rng = rng


class ListField(Field):
    type_ = list

    def __init__(self, caption, required=True, max=None):
        super(ListField, self).__init__(caption, required)
        self.max = max