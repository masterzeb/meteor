# TODO: add where, regex and other selectors

import logging
import inspect
import math

from pymongo.objectid import ObjectId

from ..helpers.lists import distinct
from ..helpers.strings import trim
from ..exceptions import SelectorError


def check_args_types(method):
    def wrapper(self, *args, **kwargs):
        # get allowed types
        allowed_types = [list(self.arg_types)]
        if hasattr(self, 'kwarg_types'):
            allowed_types.append(list(self.kwarg_types))
        else:
            allowed_types = allowed_types * 2

        # allow values to be same class as self or not
        for i, prefix in enumerate(['', 'kw']):
            allow = prefix + 'arg_types_same'
            if hasattr(self, allow):
                if getattr(self, allow):
                    allowed_types[i].append(self.__class__)
                elif self.__class__ in allowed_types[i]:
                    allowed_types[i].remove(self.__class__)

        # validate values
        for i, values in enumerate([args, [val for val in kwargs.values()]]):
            for val in values:
                if not (
                    type(val) in allowed_types[i] or (
                    isinstance(val, Selector) and \
                    any(cl in allowed_types[i] \
                        for cl in val.__class__.__mro__))):
                            raise SelectorError.value_type_exc(
                                self, i, val, allowed_types[i], len(values) > 1)
        return method(self, *args, **kwargs)
    return wrapper


def check_args_length(method):
    def wrapper(self, *args, **kwargs):
        # get summary length
        length = len(args) + len(kwargs.keys())

        # warn if empty
        if length == 0:
            self.warning(msg = '"{0}" selector gets empty array'
                .format(self.__class__.__name__))

        # warn if less than 2 because this decorator is for
        # ListSelector and ConditionalSelector only
        elif length < 2:
            self.warning(msg = '"{0}" selector gets less than 2 arguments'
                .format(self.__class__.__name__))
        return method(self, *args, **kwargs)
    return wrapper


class Selector(object):
    key = None
    quiet_output = False
    warning_index = 2

    def __and__(self, other):
        if not isinstance(other, Selector):
            raise SelectorError.operation_exc(self, other, 'and')
        Selector.warning_index += 2
        result = and_(self, other)
        Selector.warning_index -= 2
        return result

    def __or__(self, other):
        if not isinstance(other, Selector):
            raise SelectorError.operation_exc(self, other, 'or')
        Selector.warning_index += 1
        result = or_(self, other)
        Selector.warning_index -= 1
        return result

    def associate(self, key):
        # if key has not associated yet
        if not self.key:
            self.key = key

            # change key requirement
            if hasattr(self, 'require_key'):
                self.require_key = False

            # transfer key into
            if hasattr(self, 'selectors'):
                if isinstance(self.selectors, list):
                    for selector in self.selectors:
                        selector.associate(key)
                elif isinstance(self.selectors, dict):
                    for op_selectors in self.selectors.values():
                        for selector in op_selectors:
                            selector.associate(key)

    def clone(self):
        # remember quiet_output value and turn off output to
        # prevent repeating of warnings
        qo = self.quiet_output
        self.quiet_output = False

        # create new instance of self class
        if hasattr(self, 'selectors'):
            clone = self.__class__(*self.selectors)
        elif isinstance(self.val, list):
            clone = self.__class__(*self.val)
        else:
            clone = self.__class__(self.val)

        # eval expr
        if hasattr(self, 'expr'):
            clone.expr = self.expr

        # associate key
        if self.key:
            clone.associate(self.key)

        # restore quiet_output_value
        self.quiet_output = qo

        # return new object
        return clone

    def warning(self, msg, inc_index=0):
        if not self.quiet_output:
            try:
                # get stack
                index = self.warning_index + inc_index
                stack = inspect.stack()[index]

                # logging message
                msg += '. File "{0}", line {1}, in {2}'.format(
                    stack[1], stack[2], stack[3])
                logging.warn(msg)
            except IndexError:
                pass


class SimpleSelector(Selector):
    require_key = True

    @check_args_types
    def __init__(self, val):
        self.val = val
        self.expr = {'$' + self.__class__.__name__.replace('_', ''): self.val} \
            if not isinstance(self, eq) else self.val

    def __eq__(self, other):
        if not isinstance(other, Selector):
            raise SelectorError.operation_exc(self, other, 'compare')
        if (self.__class__ == other.__class__):
            if isinstance(self, SimpleSelector):
                return self.val == other.val
            else:
                return self.selectors == self.selectors
        return False

    def __and__(self, other):
        if isinstance(other, eq):
            # any selector with eq is unnecessary
            self.warning('Attemp to combine "eq" selector with other')
            if self == other:
                return self
        elif isinstance(other, self.__class__):
            # if operands are the same class - try to collapse it
            if self.collapse_same(other):
                return other
        elif isinstance(other, SimpleSelector):
            # if both are SimpleSelector and they are different - combine them
            return CombinedSelector(self, other)
        elif isinstance(other, CombinedSelector):
            # if other is CombinedSelector and it have't intersection
            # with self - combine them
            combined = self.extend_combined(other)
            if combined:
                return combined

        # default behaviour
        return super(SimpleSelector, self).__and__(other)

    def collapse_same(self, other, warning_index=0):
        if self == other:
            return True
        elif not isinstance(self, ModSelector):
            # warn if selectors are not mod
            # because different mod selectors are possible
            self.warning(
                'Attemp to combine "{0}" selectors with different values' \
                .format(self.__class__.__name__), warning_index + 1)
        return False

    def extend_combined(self, other, warning_index=0):
        # if no intersection
        if not self.__class__ in [s.__class__ for s in other.selectors]:
            return CombinedSelector(self, other)
        else:
            # iterate included selectors
            for selector in other.selectors:
                if isinstance(selector, self.__class__):
                    # if possible to collapse with self
                    if self.collapse_same(selector, warning_index + 1):
                        return other
        return None

    def prepare(self, with_key=True):
        if with_key:
            return {self.key: self.expr} if self.expr else {}
        else:
            return self.expr


class CombinedSelector(Selector):
    require_key = True
    arg_types = (SimpleSelector, )
    arg_types_same = True

    @check_args_types
    def __init__(self, *args):
        # gather selectors
        self.selectors = [s for s in args if isinstance(s, SimpleSelector)]
        for selector in args:
            if isinstance(selector, CombinedSelector):
                self.selectors.extend(selector.selectors)
        self.selectors = distinct(self.selectors)

    def __and__(self, other):
        if isinstance(other, eq):
            # any selector with eq is unnecessary
            self.warning('Attemp to combine "eq" selector with other')
            if any(sel == other for sel in self.selectors):
                return self
        elif isinstance(other, SimpleSelector):
            # if other is SimpleSelector and it have't intersection
            # with self - combine them
            combined = other.extend_combined(self)
            if combined:
                return combined
        elif isinstance(other, CombinedSelector):
            # if both operands are CombinedSelector and no intersection
            # between all included selectors - combine them
            if all(sel.extend_combined(other, 1) for sel in self.selectors):
                return CombinedSelector(self, other)
        return super(CombinedSelector, self).__and__(other)

    def prepare(self, with_key=True):
        key = self.key if with_key else None
        result = {key: {}}
        for selector in self.selectors:
            val = selector.prepare(with_key=False)
            if isinstance(selector, eq):
                result[key] = val
            else:
                result[key].update(val)
        return (result if result[key] else {}) if with_key else result.get(key)


class ConditionalSelector(Selector):
    arg_types = (Selector, )
    kwarg_types = (ObjectId, Selector, int, float, str, bool, list)
    require_key = False

    @check_args_length
    @check_args_types
    def __init__(self, *args, **kwargs):
        self.selectors = [selector for selector in distinct(args) \
           if not isinstance(selector, self.__class__)]

        # extend included selectors by selectors of the same class
        for selector in args:
            if isinstance(selector, self.__class__):
                self.selectors.extend(selector.selectors)

        if self.selectors:
            # can't create conditional selector if keyword arguments
            # given and all included selectors requires a key
            # or if not all included selectors requires a key
            all_required = all(sel.require_key for sel in self.selectors)
            if not all_required or (all_required and len(kwargs)):
                raise SelectorError.uncertain_key_exc(self)

            if any(selector.require_key for selector in self.selectors):
                self.require_key = True

        # cast keyword arguments to equal selector if need
        # associate keywords and append to selectors
        for k, v in kwargs.items():
            selector = eq(v) if not isinstance(v, Selector) else v
            selector.associate(k)
            self.selectors.append(selector)

        # warn if conditional selectors were given
        if not self.quiet_output:
            if any(isinstance(s, ConditionalSelector) for s in self.selectors):
                self.warning(
                    'Nested "and_", "or_", "nor" reduces the performance',
                    inc_index=2)

    def prepare(self):
        # TODO: optimize nested conditional selectors
        return {self.op: [sel.prepare() for sel in self.selectors]}


class ListSelector(SimpleSelector):
    arg_types = (ObjectId, int, float, str, bool, list)

    @check_args_length
    @check_args_types
    def __init__(self, *args):
        self.val = distinct(args)
        self.expr = {'$' + self.__class__.__name__.replace('_', ''): self.val} \
            if self.val else {}


class ModSelector(SimpleSelector):
    arg_types = (int, )

    @check_args_types
    def __init__(self, divider, mod):
        self.val = [divider, mod]
        self.expr = {'$mod': self.val}


class OrSelector(ConditionalSelector):
    op = '$or'


class NorSelector(ConditionalSelector):
    op = '$nor'


class AndSelector(ConditionalSelector):
    op = '$and'

    def __init__(self, *args, **kwargs):
        super(AndSelector, self).__init__(*args, **kwargs)

        # warn if and_ can be replaced with & operand for more permomance
        if not self.quiet_output and all(
            isinstance(s, (SimpleSelector, CombinedSelector)) and not \
            isinstance(s, eq) for s in args):

            selectors = [sel for sel in args if isinstance(sel, SimpleSelector)]
            for sel in args:
                if isinstance(sel, CombinedSelector):
                    selectors.extend(sel.selectors)

            criteria = lambda x: x.__class__.__name__
            if len(selectors) == len(distinct(selectors, criteria)):
                self.warning(trim(
                    '''There is better to replace "and_" selector with "&" \
                    operator for better performance'''))


class NumSelector(SimpleSelector):
    arg_types = (int, float)

class IntSelector(SimpleSelector):
    arg_types = (int, )

class BoolSelector(SimpleSelector):
    arg_types = (bool, )

class AnySelector(SimpleSelector):
    arg_types = (ObjectId, int, float, str, bool, list)


class eq(AnySelector): pass
class ne(AnySelector): pass

class lt(NumSelector): pass
class gt(NumSelector): pass
class lte(NumSelector): pass
class gte(NumSelector): pass

class nin(ListSelector): pass
class in_(ListSelector): pass
class all_(ListSelector): pass

class exists(BoolSelector): pass
class size(IntSelector): pass
class mod(ModSelector): pass

class or_(OrSelector): pass
class and_(AndSelector): pass
class nor(NorSelector): pass
