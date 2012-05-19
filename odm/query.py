import logging
import functools

from .selectors import Selector, ConditionalSelector
from ..helpers.dictonary import extend
from ..exceptions import QueryError


def query_method(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        query = Query(self)
        return getattr(query, method.__name__)(*args, **kwargs)
    return wrapper


def check_method(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if all(m.startswith('-') for m in self.allowed_methods):
            if '-' + method.__name__ in self.allowed_methods:
                raise
        elif not method.__name__ in self.allowed_methods:
            # TODO: make exception (forbidden method after self.last_method)
            raise
        self.last_method = method.__name__
        return method(self, *args, **kwargs)
    return wrapper


def check_selectors(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        selectors = {}
        for key, value in kwargs.items():
            if not isinstance(value, Selector):
                selector = eq(value)
            else:
                selector = value

            if not selector.require_key:
                raise # excess key
            selector.associate(key)
            selectors[key] = [selector]

        for selector in args:
            if selector.require_key:
                raise # no key
        if args:
            selectors[None] = list(args)

        return method(self, selectors)
    return wrapper


class Query(object):
    ''' PyMongo cursor wrapper. Provides more user-friendly query syntax. '''

    def __init__(self, scheme):
        self.scheme = scheme
        self.allowed_methods = ['filter', 'update', 'insert']

        self.methods = []
        self.args = []
        self.prepare_funcs = []

    def __iter__(self):
        return self.cursor

    @property
    def cursor(self):
        if not hasattr(self, '_cursor'):
            self._cursor = self.scheme.cursor

            for method, args, prepare_fn in zip(
                self.methods, self.args, self.prepare_funcs):
                self._cursor = getattr(self._cursor, method)(**prepare_fn(args))
            if not self.last_method == 'count' and \
               not self.scheme._meta.db_ref._quiet_output:
                    logging.debug(self.log_prefix + self.js_query)
        return self._cursor

    @property
    def js_query(self):
        if not hasattr(self, '_js_query'):
            self._js_query = 'db.{0}'.format(self.scheme.provider)
            making_rules = {
                'find': (('spec', 'fields'), None),
                'sort': (
                    ('key_or_list', ),
                    lambda x: '{' + ', '.join(["'%s': %d" % s for s in x]) + '}'
                ),
                'limit': (('limit', ), None),
                'skip': (('skip', ), None),
            }

            for method, kwargs in zip(self.methods, self.args):
                (key_seq, formatter) = making_rules[method]
                formatter = formatter or (lambda x: str(x))
                args = [formatter(kwargs[k]) for k in key_seq if k in kwargs]
                self._js_query += '.{0}({1})'.format(method, ', '.join(args))
        return self._js_query

    @property
    def log_prefix(self):
        return "Mongo query (db='{0}'): ".format(self.scheme._meta.db)

    def _extend_query(self, method, args, prepare_fn=lambda x: x):
        self.methods.append(method)
        self.args.append(args)
        self.prepare_funcs.append(prepare_fn)

    def _rewind(self):
        self.cursor.rewind()

    @check_method
    def count(self):
        count = self.cursor.count()
        logging.debug(self.log_prefix + self.js_query + '.count()')
        return count

    def fetch(self):
        # TODO: realize
        # instance will object or dict. Result is always tuple.
        # after that - rewind cursor
        pass

    @check_selectors
    @check_method
    def filter(self, selectors):
        # define allowed methods
        self.allowed_methods = ['-insert', '-one']

        if not self.methods:
            # define prepare function
            def prepare_fn(args):
                selectors_dict = args['spec']
                conditionals = []
                result = {}
                for k, v in selectors_dict.items():
                    if isinstance(v, list):
                        if k is None:
                            conditionals.extend(v)
                        else:
                            conditionals.extend([s for s in v if \
                                isinstance(s, ConditionalSelector)])
                            selectors = [s for s in v if \
                                not isinstance(s, ConditionalSelector)]

                            if selectors:
                                sel = selectors[0]
                                for s in selectors[1:]:
                                    sel = sel & s

                                sel.associate(k)
                                result.update(sel.prepare())
                    elif isinstance(v, ConditionalSelector):
                        conditionals.append(v)
                    else:
                        result.update(v.prepare())

                if conditionals:
                    for op in ['$and', '$or', '$nor']:
                        op_selectors = [s for s in conditionals if s.op == op]
                        if len(op_selectors) == 1:
                            result.update(op_selectors[0].prepare())
                        elif len(op_selectors):
                            result.update({
                                '$and': [s.prepare() for s in op_selectors]
                            })
                args['spec'] = result
                return args

            # extend query
            self._extend_query(
                method='find', args={'spec': selectors}, prepare_fn=prepare_fn)
        else:
            self.args[0]['spec'] = extend(self.args[0]['spec'], selectors)
        return self

    @check_method
    def one(self, *args, **kwargs):
        return self.filter(*args, **kwargs).limit(1)[0]

    @check_method
    def sort(self, *fields):
        self.allowed_methods = ['limit', 'skip', 'sort', 'subset']
        sorting = [(k.lstrip('-'), -1 if k[0] == '-' else 1) for k in fields]
        if 'sort' in self.methods:
            self.args[self.methods.index('sort')]['key_or_list'].extend(sorting)
        else:
            self._extend_query(method='sort', args={'key_or_list': sorting})
        return self

    @check_method
    def subset(self, *fields):
        self.allowed_methods = ['limit', 'skip', 'sort', 'subset']

        subset = {f.lstrip('-'): int(f[0] != '-') for f in fields}
        if 'id' in subset:
            subset['_id'] = subset['id']
            del subset['id']

        subset.update(self.args[0].get('fields', {}))
        if '_id' in subset:
            del subset['_id']

        if 0 in subset.values() and 1 in subset.values():
            raise QueryError.subset_uniform_exc(subset)

        if not '_id' in subset and 1 in subset.values():
            subset['_id'] = 0

        # extend find operation
        self.args[0]['fields'] = subset
        return self

    @check_method
    def insert(self):
        # TODO: realize
        # return lastError if safe else None
        pass

    @check_method
    def update(self):
        # TODO: realize
        # return lastError if safe else None
        pass

    @check_method
    def create(self):
        # TODO: realize
        # creates new instance and then save it
        pass

    def refresh(self):
        self.cursor._rewind()
        self.cursor._refresh()
