import importlib
import inspect
import os
import sys

from .handlers import EventHandler, View
from .forms import Form
from .odm.core import DocumentMeta, Document


class Package(object):
    def __init__(self, module):
        self.module = module
        self.name = module.__name__
        self.description = getattr(module, 'description', '')

        self.schemes = []
        self.views = []
        self.handlers = []
        self.forms = []

        # TODO: rewrite try/except to os.path.exists cause ImportError may be
        # in module
        try:
            # gather schemes
            schemes = importlib.import_module('.schemes', module.__package__)
            for name, obj in inspect.getmembers(schemes):
                if type(obj) == DocumentMeta and obj != Document:
                    self.schemes.append(obj)
        except ImportError:
            pass

        try:
            # gather views
            views = importlib.import_module('.views', module.__package__)
            for name, obj in inspect.getmembers(views):
                if inspect.isclass(obj):
                    if not obj == View and View in obj.__mro__:
                        self.views.append(obj)
        except ImportError:
            pass

        try:
            # gather handlers
            handlers = importlib.import_module('.handlers', module.__package__)
            for name, obj in inspect.getmembers(handlers):
                if inspect.isclass(obj):
                    if not obj == EventHandler and EventHandler in obj.__mro__:
                        self.handlers.append(obj)
        except ImportError:
            pass

        try:
            # gather forms
            forms = importlib.import_module('.forms', module.__package__)
            for name, obj in inspect.getmembers(forms):
                if inspect.isclass(obj):
                    if not obj == Form and Form in obj.__mro__:
                        self.forms.append(obj)
        except ImportError:
            pass


class PackagesManager(object):
    def __init__(self, exclude=()):
        self.packages = []

        app_path = sys.path[0]
        for f in [f for f in os.listdir(app_path) if not f.startswith('.')]:
            if not f in exclude:
                module = None
                if os.path.isdir(os.path.join(app_path, f)):
                    try:
                        if f in sys.modules:
                            module = sys.modules[f]
                        else:
                            module = importlib.import_module(f)
                    except ImportError:
                        pass
                if getattr(module, 'meteor_package', False):
                    self.packages.append(Package(module))

        # add welcome module if no views exists
        if not self.get_all('views'):
            welcome = importlib.import_module('meteor.welcome')
            self.packages.append(Package(welcome))

    def get_all(self, name):
        items = []
        for package in self.packages:
            items.extend(getattr(package, name, []))
        return items

    def get_package(self, cls, name='views'):
        for package in self.packages:
            if cls in getattr(package, name, []):
                return package
