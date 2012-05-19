import sys
import functools

from pymongo.connection import Connection
from pymongo.son_manipulator import SONManipulator
from pymongo.objectid import ObjectId

from ..exceptions import (SchemaError, ValidationError,
    InitializationError, ClassmethodError)

from ..helpers.plural import Plural
from ..helpers.decorators import classproperty

from .query import Query, query_method
from .fields import Field
from .selectors import Selector


class odmclassmethod(object):
    ''' Classmethod decorator which forbid to call method by class instances '''

    def __init__(self, method):
        self.method = method

    def __get__(self, instance, cls):
        if instance:
            raise ClassmethodError.called_by_instance_exc(
                self.method.__name__, cls.__module__, cls.__name__)
        return lambda *args, **kwargs: self.method(cls, *args, **kwargs)


class ConvertToObject(SONManipulator):
    '''
    Serialized Ocument Notation manupulator.
    Returns an instance of the appropriate collection.
    '''

    def __init__(self, db):
        self.db = db

    def transform_outgoing(self, son, collection):
        ''' Convert response to objects. Returns a value only if it is one '''

        if collection._Collection__name == '$cmd':
            return son
        if len(son.keys()) == 1:
            for k, v in son.items():
                if k == '_id':
                    return ObjectId(v)
                else:
                    coll = getattr(self.db, collection._Collection__name)
                    field = (getattr(coll, k))
                    return field.type_(v)
        else:
            if '_id' in son:
                son['id'] = son['_id']
                del son['_id']
            cls = getattr(self.db, collection._Collection__name)
            return cls({'new': False, 'no_validation': True}, **son)


class Database(object):
    '''
    Database provides access to its collections by collection class name and
    collection alias. It automatically gather all imported classes inherited
    of "Document" and classes derived from "Document" and make references to
    them if they belongs to this database (determined by __db__ attribute,
    if it missing it is consider that collection belongs to first created db).

    It should be remembered that class inherited of "Document" or of the class
    derived from "Document" and containing at least one instance of "Field"
    class as attribute is collection!

    Database automatically setup missing aliases if possible by make plural
    in lower case. Also it automatically assign cross-references.

    To create you must specify database name, host and port
    Host is '127.0.0.1' by default
    Port is 27017 by default

    Optionally you can pass two additional arguments:
    gen_ids - to generate object id at client side
    change_builtins - to add query selectors in __builtins__
    Both of them are True by default

    quiet_output - to hide warning
    False by default

    To see full database info just type
    >>> db = Database(name, host, port)
    >>> print(db)
    '''

    @property
    def name(self):
        return self._name

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    def __init__(self, db_name='test', host='127.0.0.1', port=27017,
            gen_ids=True, change_builtins=True, quiet_output=False):
        # adding selectors to __builtins__
        if change_builtins:
            from string import ascii_lowercase as ascii_lc
            from meteor.odm import selectors
            for selector in [getattr(selectors, name) \
                for name in dir(selectors) if name[0] in ascii_lc]:
                    __builtins__[selector.__name__] = selector

        # set quiet output if need
        Selector.quiet_output = quiet_output

        # connect to mongo
        self._name = db_name
        self._host = host
        self._port = port
        self._genids = gen_ids
        self._quiet_output = quiet_output

        self._connection = Connection(host, port)[db_name]

        # add converter
        self._connection.add_son_manipulator(ConvertToObject(self))

        # declare vars
        self._collections = {}
        collections = set()

        # gather collections
        # TODO: replace with module manager
        for module in sys.modules.values():
            for cls in module.__dict__.values():
                if type(cls) == DocumentMeta \
                    and len([f for f in cls.__dict__.values() \
                        if isinstance(f, Field)]) \
                    and (not hasattr(cls._meta, '_db') \
                        or cls._meta._db == self.name):
                            collections.add(cls)

        # create plural maker
        plural = Plural()

        # take the collections that belong to this database
        # or do not belong to anything and set aliases and references for each
        for coll in collections:
            # gather fields
            coll._meta.fields = ['id'] + sorted([
                k for k, v in coll.__dict__.items() if isinstance(v, Field) \
                and k != 'id'
            ])

            # occupy collection and set reference to this database
            setattr(coll._meta, 'db', self._name)
            setattr(coll._meta, 'db_ref', self)

            if hasattr(coll._meta, 'alias') and \
                coll._meta.alias.startswith('_'):
                raise SchemaError.metadata_naming_exc(
                    coll._meta.alias, coll.__module__, coll.__name__)

            if not hasattr(coll._meta, 'alias'):
                # no alias was given
                coll._meta.alias = plural.make(coll.__name__)

            if not hasattr(self, coll.__name__):
                # collection name is free
                setattr(self, coll.__name__, coll)
            elif hasattr(self, coll._meta.alias):
                # collection name or alias must be free
                raise SchemaError.collection_binding_exc(coll)

            if not hasattr(self, coll._meta.alias):
                # alias name is free
                setattr(self, coll._meta.alias, coll)

            # add to database collections by provider name
            self._collections[coll.provider] = coll

    def __repr__(self):
        return '<{0}.Database({1}, {2}@{3}:{4})>'.format(
            self.__module__,
            '{\n    %s\n}' % ',\n    '.join(
                '"{0}": {1}.{2}({3})'.format(
                    k, v.__module__, v.__name__, ', '.join(v._meta.fields)
                ) for k, v in self._collections.items()
            ) if self._collections else 'no collections',
            self.name, self.host, self.port
        )

    @classmethod
    def make_new_id(self):
        return ObjectId() if self._meta.db_ref._genids else None


class DocumentMeta(type):
    ''' Metaclass for all documents. '''

    def __new__(self, *args):
        # assign MetaData
        class MetaData: pass
        if not 'MetaData' in args[2]:
            args[2]['_meta'] = MetaData
        else:
            args[2]['_meta'] = args[2]['MetaData']
            del args[2]['MetaData']

        # verification of field names
        for field in [k for k, v in args[2].items() if isinstance(v, Field)]:
            if '__' in field:
                raise SchemaError.field_naming_exc(
                    field, args[2]['__module__'], args[0])
        return type.__new__(self, *args)

    def __call__(self, *opts, **fields):
        # parse options
        options = opts[0] if len(opts) else {}

        # is object new or fetched from db
        new = options.get('new', True)
        # prevent fields validation or not
        no_validation = options.get('no_validation', False)

        # create document
        document = type.__call__(self)

        for field_name in fields.keys():
            if not field_name in self._meta.fields:
                raise InitializationError.illegal_argument_exc(
                    self.__name__, field_name)

        if not no_validation:
            # TODO: validate fields
            pass

        # assign values to fields
        for field in self._meta.fields:
            if field != 'id':
                value = None
                if field in fields:
                    value = getattr(self, field).type_(fields[field])
                setattr(document, field, value)
            else:
                id_ = None
                if 'id' in fields:
                    id_ = fields['id']
                elif new:
                    id_ = Database.make_new_id()
                setattr(document, 'id', id_)

        return document


class Document(object, metaclass=DocumentMeta):
    '''
    Basic class of collection.
    So named Document because the instances of this class are documents.
    '''

    @classproperty
    def provider(self):
        return self._meta.alias if \
            hasattr(self._meta, 'alias') else self.__name__

    @classproperty
    def cursor(self):
        if hasattr(self._meta, 'db_ref'):
            return self._meta.db_ref._connection[self.provider]

    @odmclassmethod
    @query_method
    def filter(self, *args, **kwargs):
        pass

    @classproperty
    def all(self):
        return Query(self).filter()

    @odmclassmethod
    @query_method
    def one(self, *args, **kwargs):
        pass

    @odmclassmethod
    def count(self):
        return self.cursor.count()
