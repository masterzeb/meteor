from .helpers.strings import capfirst, trim


class MeteorError(Exception):
    ''' Basically exception class. '''

    def __init__(self, msg):
        super(MeteorError, self).__init__(trim(msg))


class ClassmethodError(MeteorError):
    @classmethod
    def called_by_instance_exc(self, name, module, schema):
        return self(
            '''Document classmethod "{0}" can not be called by an instance \
            of class "{1}.{2}"'''.format(name, module, schema)
        )


class InitializationError(MeteorError):
    @classmethod
    def empty_fieldset_exc(self, classname):
        return self(
            'Can not create "{0}" instance with empty fieldset'\
            .format(classname)
        )

    @classmethod
    def illegal_argument_exc(self, classname, arg):
        return self(
            '{0}.__init__() takes illegal argument "{1}"' \
            .format(classname, arg)
        )


class ModifierError(MeteorError):
    @classmethod
    def arg_type_exc(self, modifier, value):
        return self(
            'Arguments of modifier "{0}" must be "{1}", not "{2}".'
            .format(
                modifier.__class__.__name__,
                '" or "'.join([str(t.__name__) for t in modifier.arg_types]),
                type(value).__name__
            )
        )

    @classmethod
    def associate_exc(self, modifier, instance):
        return self('"{0}" modifier could be assigned to {1}, not to "{2}"' \
            .format(
                modifier.__class__.__name__,
                ' or '.join('"%s"' % cls.__name__ for cls in modifier.for_),
                instance.__class__.__name__
            )
        )

    @classmethod
    def selector_exc(self, selector):
        return self(
            '''"pull" modifier may takes "SimpleSelector" or "CombinedSelector"\
            not "ConditionalSelector" ("{0}")''' \
            .format(selector.__class__.__name__)
        )


class SchemaError(MeteorError):
    @classmethod
    def collection_binding_exc(self, collection):
        return self(
            '''Can not use nor the class name "{0}" nor the alias "{1}" as
            collection binding - both of them already in use. \
            Try switch to another.''' \
            .format(collection.__name__, collection._meta.alias)
        )

    @classmethod
    def field_naming_exc(self, name, module, schema):
        return self(
            '''Field name "{1}" of schema "{2}.{3}" has the wrong name. Try \
            switch to another.\nDescription: to avoid naming conflicts field \
            name can not contains double underscores.''' \
            .format(name, module, schema)
        )

    @classmethod
    def metadata_naming_exc(self, type_, name, module, schema):
        return self(
            '''{0} name "{1}" of schema "{2}.{3}" has the wrong name. Try \
            switch to another.\nDescription: to avoid naming conflicts \
            metadata can not starts with "_"''' \
            .format(name, module, schema)
        )


class SelectorError(MeteorError):
    ''' Selector exception '''

    @classmethod
    def operation_exc(self, sel_1, sel_2, op_type):
        return self(
            '''{0} operation is applicable between instances of the \
            "Selector" subclasses, not between "{1}" and "{2}" ''' \
                .format(capfirst(op_type), sel_1.__class__.__name__,
                sel_2.__class__.__name__)
        )

    @classmethod
    def uncertain_key_exc(self, selector):
        return self(
            '''Can not create a conditional selector "{0}" with an uncertain \
            key.\nDescription: non-keyword arguments requires a key and \
            keyword arguments was given or not all non-keyword arguments \
            requires a key.'''
            .format(selector.__class__.__name__)
        )

    @classmethod
    def value_type_exc(self, selector, kw, value, types, many=False):
        return self(
            '{0} value{1} of selector "{2}" must be "{3}", not "{4}".'.format(
                'Keyword' if kw else 'Non-keyword',
                's' if many else '', selector.__class__.__name__,
                '" or "'.join([str(t.__name__) for t in types]),
                type(value).__name__
            )
        )


class QueryError(MeteorError):
    @classmethod
    def excess_key_exc(self, key, selector):
        return self(
            'Excess key "{0}" for "{1}" selector in query method "filter"' \
            .format(key, selector.__class__.__name__)
        )

    @classmethod
    def fetch_exc(self, cast_type):
        return self(
            '''Argument "cast_to" of query method "fetch" must be "object" or \
            "dict" not "{0}"'''.format(cast_type)
        )

    @classmethod
    def forbidden_method_exc(self, method, last_method):
        return self('"{0}" method can not be used after "{1}" method' \
            .format(method, last_method))

    @classmethod
    def illegal_key_exc(self, method, key):
        return self(
            'Query method "{0}" takes illegal keyword argument "{1}"' \
            .format(method, key)
        )

    @classmethod
    def slice_steps_exc(self):
        return self('Query instances does not support slice steps')

    @classmethod
    def special_args_exc(self, arg_type, needed_types, key=None):
        return self('Special {0}keyword argument{1} must be {2}, not "{3}"' \
            .format(
                'non-' if not key else '', ' "%s"' % key if key else 's',
                ' or '.join('"%s"' % t.__name__ for t in needed_types) if \
                    isinstance(needed_types, tuple) else \
                    '"%s"' % needed_types.__name__,
                arg_type.__name__
            )
        )

    @classmethod
    def subscribe_exc(self):
        return self(
            '''Query object subscribing supports slicing and indexing by int \
            only. \nDescription: If you want to access data you should \
            subscribe query.data object'''
        )

    @classmethod
    def subset_uniform_exc(self, subset):
        return self(
            '''Subset must be either the inclusion or exclusion of fields.\
            \nDescription: subset query contains {0}'''.format(str(subset))
        )
