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
    def illegal_argument_exc(self, classname, arg):
        return self(
            '{0}.__init__() takes illegal argument "{1}"' \
            .format(classname, arg)
        )


class SchemaError(MeteorError):
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

    @classmethod
    def collection_binding_exc(self, collection):
        return self(
            '''Can not use nor the class name "{0}" nor the alias "{1}" as
            collection binding - both of them already in use. \
            Try switch to another.''' \
            .format(collection.__name__, collection._meta.alias)
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
    def value_type_exc(self, selector, kw, value, types, many=False):
        return self(
            '{0} value{1} of selector "{2}" must be "{3}", not "{4}".'.format(
                'Keyword' if kw else 'Non-keyword',
                's' if many else '', selector.__class__.__name__,
                '" or "'.join([str(t.__name__) for t in types]),
                type(value).__name__
            )
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


class QueryError(MeteorError):
    @classmethod
    def subset_uniform_exc(self, subset):
        return self(
            '''Subset must be either the inclusion or exclusion of fields.\
            \nDescription: subset query contains {0}'''.format(str(subset))
        )

    @classmethod
    def fetch_exc(self):
        return self()


class ValidationError(MeteorError):
    @classmethod
    def missing_exc(self, fieldname, classname):
        return self(
            'Missing field "{0}" for instance of class "{1}"' \
            .format(fieldname, classname)
        )

    @classmethod
    def type_exc(self, fieldname, classname, type_):
        return self(
            'Value of field "{0}" must be "{1}" for instance of class "{2}"' \
            .format(fieldname, type_, classname)
        )