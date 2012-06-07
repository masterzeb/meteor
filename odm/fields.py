# TODO: rewrite Field class. Make it descriptor with type saving,
# TODO: Field must working with validators
# TODO: no data except type and index don't stored in Field


class Field(object):
    pass


class StringField(Field):
    type_ = str


class IntegerField(Field):
    type_ = int


class ListField(Field):
    type_ = list


class BooleanField(Field):
    type_ = bool

