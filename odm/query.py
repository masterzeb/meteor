import logging

from .selectors import Selector, ConditionalSelector
from .modifiers import Modifier, set_
from ..helpers.dictonaries import extend
from ..exceptions import QueryError


def query_method(method):
    def wrapper(self, *args, **kwargs):
        query = Query(self)
        return getattr(query, method.__name__)(*args, **kwargs)
    return wrapper

def check_method(method):
    def wrapper(self, *args, **kwargs):
        if hasattr(self, 'last_method'):
            exc = QueryError.forbidden_method_exc(
                method.__name__, self.last_method)
            if all(m.startswith('-') for m in self.allowed_methods):
                if '-' + method.__name__ in self.allowed_methods:
                    raise exc
            elif not method.__name__ in self.allowed_methods:
                raise exc
        self.last_method = method.__name__
        return method(self, *args, **kwargs)
    return wrapper

def check_special_args(method):
    def wrapper(self, *args, **kwargs):
        for arg in args:
            if not isinstance(arg, bool):
                raise QueryError.special_args_exc(type(arg), bool)
        for k, v in kwargs.items():
            if k.endswith('__'):
                if k == 'raw__':
                    if not isinstance(v, dict):
                        raise QueryError.special_args_exc(type(v), dict, k)
                elif not isinstance(v, bool):
                    raise QueryError.special_args_exc(type(v), bool, k)
        return method(self, *args, **kwargs)
    return wrapper

def set_safe_mode(method):
    def wrapper(self, safe__=None, *args, **kwargs):
        # get database options
        opts = {'safe': self.scheme._meta.db_ref.safe_mode}
        opts.update(self.scheme._meta.db_ref.safe_opts)

        if isinstance(safe__, bool):
            opts = {'safe': safe__}
        elif isinstance(safe__, dict):
            opts['safe'] = True
            opts.update(safe__)
        elif safe__ is not None:
            raise QueryError.special_args_exc(
                type(safe__), (dict, bool), 'safe__')
        self._safe_opts = opts
        return method(self, *args, **kwargs)
    return wrapper


class Query(object):
    ''' PyMongo cursor wrapper. Provides more user-friendly query syntax. '''

    def __init__(self, scheme):
        self.scheme = scheme
        self.allowed_methods = ['count', 'create', 'filter', 'remove']

        self.methods = []
        self.args = []
        self.prepare_funcs = []

    def __iter__(self):
        self._rewind()
        return self.cursor

    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.step:
                raise QueryError.slice_step_exc()

            if key.stop == key.start:
                return self

            limit = skip = 0
            if (key.stop and key.stop < 0) or (key.start and key.start < 0):
                count = self.scheme.count()
            if key.start:
                skip = key.start if key.start >= 0 else count + key.start
            if key.stop:
                limit = key.stop if key.stop >=0 else count + key.stop
                if key.start:
                    limit -= key.start if key.start > 0 else (count + key.start)
                if limit <= 0:
                    self._is_empty = True
                    return self

        elif isinstance(key, int):
            limit = 1
            skip = self.scheme.count() + key if key < 0 \
                else (key if key > 0 else 0)
        else:
            raise QueryError.subscribe_exc()
        return self.skip(skip).limit(limit)

    @property
    def cursor(self):
        if not hasattr(self, '_cursor'):
            self._cursor = self.scheme.cursor

            for method, args, prepare_fn in zip(
                self.methods, self.args, self.prepare_funcs):
                self._cursor = getattr(self._cursor, method)(**prepare_fn(args))
            if not self.scheme._meta.db_ref.quiet_output:
                safe = None
                if not self.methods[0] == 'find':
                    safe_opts =\
                        self._safe_opts if hasattr(self, '_safe_opts') else {}
                    if safe_opts.get('safe', None):
                        del safe_opts['safe']
                        safe = ', safe({0})'.format(str(safe_opts or ''))
                logging.debug("Mongo query (db='{0}'{1}): {2}".format(
                    self.scheme._meta.db, safe or '', self.js_query))
        return self._cursor

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = self.fetch()
        return self._data

    @property
    def js_query(self):
        if not hasattr(self, '_js_query'):
            self._js_query = 'db.{0}'.format(self.scheme.provider)
            making_rules = {
                'count': ((), None),
                'find': (('spec', 'fields'), None),
                'insert': (('doc_or_docs', ), None),
                'limit': (('limit', ), None),
                'remove': (('spec_or_id', ), None),
                'sort': (
                    ('key_or_list', ),
                    lambda x: '{' + ', '.join(["'%s': %d" % s for s in x]) + '}'
                ),
                'skip': (('skip', ), None),
                'update': (('spec', 'document', 'upsert', 'multi'), None)
            }

            for method, kwargs in zip(self.methods, self.args):
                (key_seq, formatter) = making_rules[method]
                formatter = formatter or (lambda x: str(x))
                args = [formatter(kwargs[k]) for k in key_seq if k in kwargs]
                self._js_query += '.{0}({1})'.format(method, ', '.join(args))
        return self._js_query.replace('None', 'null') \
            .replace('True', 'true').replace('False', 'false')


    def _extend_query(self, method, args={}, prepare_fn=lambda x: x):
        self.methods.append(method)
        self.args.append(args)
        self.prepare_funcs.append(prepare_fn)

    def _rewind(self):
        self.cursor.rewind()

    @check_method
    def count(self):
        self._extend_query(method='count')
        return self.cursor

    def fetch(self, cast_to=object):
        if hasattr(self, '_is_empty') and self._is_empty:
            return tuple()
        if cast_to == object:
            data = (x for x in self)
        elif cast_to == dict:
            data = (x.__dict__ for x in self)
        else:
            raise QueryError.fetch_exc(type(cast_to))
        self._rewind()
        return tuple(data)

    @check_method
    def filter(self, *args, **kwargs):
        # define allowed methods and get allowed keys
        self.allowed_methods = ['-create', '-one']
        allowed_keys = self.scheme._meta.fields

        # get raw argumet if exist
        raw = kwargs.get('raw__', {})
        if 'raw__' in kwargs:
            del kwargs['raw__']

        # define validate key function
        def validate_key(selector):
            if not selector.key:
                for nested_selector in selector.selectors:
                    validate_key(nested_selector)
            elif selector.key not in allowed_keys:
                raise QueryError.illegal_key_exc('filter', selector.key)

        # parse and check selectors
        selectors = {}
        for key, value in kwargs.items():
            if not isinstance(value, Selector):
                selector = eq(value)
            else:
                selector = value

            if not selector.require_key:
                raise QueryError.excess_key_exc(key, selector)
            selector.associate(key)
            selectors[key] = [selector]

        for selector in args:
            if selector.require_key:
                raise # TODO: make exception - no key
        if args:
            selectors[None] = list(args)

        for selectors_list in selectors.values():
            for selector in selectors_list:
                validate_key(selector)

        if not self.methods:
            # define prepare function
            def prepare_fn(args):
                spec_key = 'spec' if 'spec' in args else 'spec_or_id'
                selectors_dict = args.get(spec_key, {})
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
                args[spec_key] = result
                args[spec_key].update(args['raw__'])
                del args['raw__']
                return args


            # extend query
            self._extend_query(method='find', prepare_fn=prepare_fn,
                args={'spec': selectors, 'raw__': raw})
        else:
            self.args[0]['spec'] = extend(self.args[0]['spec'], selectors)
            self.args[0]['raw__'].update(raw)
        return self

    @check_method
    def one(self, *args, **kwargs):
        return self.filter(*args, **kwargs)[0].data[0]

    @check_method
    def limit(self, limit):
        if limit:
            self.allowed_methods = ['sort', 'skip', 'subset']
            self._extend_query(method='limit', args={'limit': limit})
        return self

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
    def skip(self, skip):
        if skip:
            self.allowed_methods = ['limit', 'sort', 'subset']
            self._extend_query(method='skip', args={'skip': skip})
        return self

    @check_method
    def subset(self, *fields):
        self.allowed_methods = ['limit', 'skip', 'sort', 'subset']

        subset = {f.lstrip('-'): int(f[0] != '-') for f in fields}
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

    @set_safe_mode
    @check_special_args
    @check_method
    def update(self, multi__=True, upsert__=False, **kwargs):
        # get raw argumet if exist
        raw = kwargs.get('raw__', {})
        if 'raw__' in kwargs:
            del kwargs['raw__']

        modifiers = raw
        for k, v in kwargs.copy().items():
            if not k in self.scheme._meta.fields:
                raise QueryError.illegal_key_exc('update', k)
            if not isinstance(v, Modifier):
                v = set_(v)
            v.associate(k, getattr(self.scheme, k))
            modifiers = extend(modifiers, v.prepare())


        # overwrite filter method
        self.methods = ['update']
        self.args[0].update(self._safe_opts)
        self.args[0].update({
            'document': modifiers,
            'multi': multi__,
            'upsert': upsert__
        })

        # exec query
        return self.cursor

    @set_safe_mode
    @check_special_args
    @check_method
    def create(self, validation__=True, **kwargs):
        # create instance
        instance = self.scheme(validation__=validation__, **kwargs)
        if instance._id:
            kwargs['_id'] = instance._id

        # extend query
        args = {
            # TODO: may be formatted instance.__dict__ instead of kwargs?
            'doc_or_docs': kwargs,
            'manipulate': True,
            'check_keys': False
        }
        args.update(self._safe_opts)
        self._extend_query(method='insert', args=args)

        # exec query
        _id = self.cursor
        if not instance._id:
            instance._id = _id
        return instance

    def refresh(self):
        self.cursor._rewind()
        self.cursor._refresh()

    @set_safe_mode
    @check_method
    def remove(self):
        # overwrite filter method or extend query if no filter execution
        if len(self.methods):
            self.methods = ['remove']
            if 'spec' in self.args[0]:
                self.args[0]['spec_or_id'] = self.args[0]['spec']
                del self.args[0]['spec']
            self.args[0].update(self._safe_opts)
        else:
            self._extend_query(method='remove', args=self._safe_opts)

        # exec query
        return self.cursor
