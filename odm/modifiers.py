from pymongo.objectid import ObjectId

from .selectors import Selector, SimpleSelector, CombinedSelector
from .fields import Field, IntegerField, ListField
from ..exceptions import ModifierError


def check_args_types(method):
    def wrapper(self, *args):
        for arg in args:
            if not any(isinstance(arg, cls) for cls in self.arg_types):
                if isinstance(arg, Selector):
                    raise ModifierError.selector_exc(arg)
                raise ModifierError.arg_type_exc(self, arg)
        return method(self, *args)
    return wrapper


class Modifier(object):
    for_ = (Field, )
    arg_types = (ObjectId, int, float, str, bool, list)

    @check_args_types
    def __init__(self, val):
        self.val = val

    def associate(self, key, instance):
        if not any(isinstance(instance, cls) for cls in self.for_):
            raise ModifierError.associate_exc(self, instance)
        self.key = key

    def prepare(self):
        op = self.op if hasattr(self, 'op') else \
            '$' + self.__class__.__name__.rstrip('_')
        return {op: {self.key: self.val}}


class set_(Modifier):
    pass


class add_to_set(Modifier):
    for_ = (ListField, )

    @check_args_types
    def __init__(self, val, *values):
        self.val = {'$each': [val] + list(values)} if len(values) else val
        self.op = '$addToSet'


class inc(Modifier):
    for_ = (IntegerField, )
    arg_types = (int, )

    @check_args_types
    def __init__(self, val):
        self.val = val


class pop(Modifier):
    for_ = (ListField, )
    arg_types = (bool, )

    @check_args_types
    def __init__(self, first=False):
        self.val = -1 if first else 1


class push(Modifier):
    for_ = (ListField, )

    @check_args_types
    def __init__(self, val, *values):
        if len(values):
            self.val = [val] + list(values)
            self.op = 'pushAll'
        else:
            self.val = val


class pull(Modifier):
    for_ = (ListField, )
    arg_types = (SimpleSelector, CombinedSelector, ObjectId,
        int, float, str, bool, list)

    @check_args_types
    def __init__(self, val, *values):
        if isinstance(val, (SimpleSelector, CombinedSelector)):
            self.val = val.prepare(False)
        elif len(values):
            self.val = [val] + list(values)
            self.op = 'pullAll'
        else:
            self.val = val
