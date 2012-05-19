import functools

class classproperty(object):
    '''
    Read-only class property decorator
    Be aware: when you call getattr(class, name) you're sure that all the class
    attrs used inside property already assigned, but it is not always the case.
    '''

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)
