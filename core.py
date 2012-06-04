import ast
import configparser
import inspect
import logging
import os
import sys

import tornado.httpserver
import tornado.ioloop
import tornado.locale
import tornado.web

from string import ascii_lowercase

from .client import StaticManager
from .handlers import EventHandler, View, WSConnection
from .helpers import log
from .helpers.dictonaries import extend
from .odm import selectors
from .odm import modifiers
from .odm.core import Database
from .packages import PackagesManager, Package


class Application(tornado.web.Application):
    def __init__(self, extra_handlers=(), extra_settings={}, extra_packages=(),
            exclude_packages=(), extra_static_libs_requirements={}):

        # define paths
        app_path = sys.path[0]

        # configure app
        (self.address, self.port), databases, settings, \
            self.views_metadata, log_config,= Configurator(app_path).data

        # gather packages
        self.package_manager = PackagesManager(exclude_packages)
        for package in extra_packages:
            if not isinstance(package, Package):
                raise # TODO: make expression - non-Package in extra_packages
            if not package.name in exclude_packages:
                self.package_manager.packages.append(package)

        # creating databases
        self.databases = {}
        models = self.package_manager.get_all('models')
        for alias, opts in databases.items():
            opts['models'] = models
            self.databases[alias] = Database(**opts)

        # make routes
        self.router = Router(self.package_manager.packages)
        handlers = self.router.routes

        # configure logging
        log.configure(**log_config)

        # extend by extra params
        handlers.extend(extra_handlers)
        settings.update(extra_settings)

        # define static path
        if not 'static_path' in settings:
            settings['static_path'] = os.path.join(app_path, 'static')

        # gather static libs
        requirements = {'meteor.js': ['jquery', 'underscore']}
        requirements = extend(requirements, extra_static_libs_requirements)
        self.static_manager = StaticManager(settings['static_path'],
            requirements, self.package_manager.packages)

        # call parent __init__ method
        super(Application, self).__init__(handlers, **settings)

    def run(self):
        try:
            http_server = tornado.httpserver.HTTPServer(self)
            http_server.listen(address=self.address, port=self.port)
            logging.info('Application started on %s:%d' % (self.address,
                self.port))
            tornado.ioloop.IOLoop.instance().start()
        except Exception as error:
            logging.error('Application failed. Details: %s' % error)


class Configurator(object):
    def __init__(self, app_path):
        # parse application config
        config = configparser.ConfigParser()
        config.read(os.path.join(app_path, 'config.cfg'))

        # define default values
        address = 'localhost'
        port = 8888
        log_config = {'level': 'info', 'colored': False}
        quiet_output = True

        settings = {}
        databases = {}

        # TODO: if must be ordered dict - check!
        for k, v in config.items():
            # transform incoming options
            opts = {k:self.transform_str(v) for k,v in dict(v).items()}

            if k == 'global':
                log_config['colored'] = opts.get('colored_output', False)
                quiet_output = not opts.get('debug', True)
                settings['debug'] = opts.get('debug', True)
                settings['default_locale'] = opts.get('default_locale', 'en')
                settings['use_compressed_static'] =\
                    opts.get('use_compressed_static', False)

                if opts.get('debug', False):
                    log_config['level'] = 'debug'
                if opts.get('change_builtins', False):
                    self._import_selectors_and_modifiers()
            elif k == 'server':
                address = opts.get('host', 'localhost')
                port = opts.get('port', 8888)
            elif k == 'settings':
                settings.update(opts)
            elif k.startswith('database'):
                alias = k.split(':')[1]
                opts['quiet_output'] = quiet_output
                opts['port'] = opts['port']
                databases[alias] = opts

        config = configparser.ConfigParser()
        config.read(config.read(os.path.join(app_path, 'views.cfg')))

        views_metadata = {'meta': []}
        for k, v in config.items():
            # transform incoming options
            opts = {k:self.transform_str(v) for k,v in dict(v).items()}
            if k == 'global':
                views_metadata['doctype'] = opts.get('doctype', None)
                views_metadata['title'] = opts.get('title', None)
                views_metadata['favicon'] = opts.get('favicon', None)
                views_metadata['meta'].append(
                    {'charset': opts.get('charset', 'utf-8')}
                )
            elif k == 'http-equiv-meta':
                views_metadata['meta'].extend([
                    {'http-equiv': k, 'content': v} for k,v in opts.items()
                ])
            elif k == 'named-meta':
                views_metadata['meta'].extend([
                    {
                        'name': k,
                        'content': v if k != 'keywords' else ', '.join(v)
                    } for k, v in opts.items()
                ])

        self._data = ((address, port), databases, settings,
            views_metadata, log_config)

    @property
    def data(self):
        for item in self._data:
            yield item

    def _import_selectors_and_modifiers(self):
        # adding selectors and modifiers to __builtins__
        for module in (selectors, modifiers):
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name[0] in ascii_lowercase:
                    __builtins__[name] = obj

    def transform_str(self, string):
        try:
            return ast.literal_eval(string)
        except:
            return string


class Router(object):
    def __init__(self, packages):
        self.routes = [('/ws_connection/?', WSConnection)]
        self.events = {}

        for package in packages:
            for view in getattr(package, 'views', []):
                if hasattr(view, 'url'):
                    url = r'{0}{1}?'.format(
                        view.url, '/' if not view.url.endswith('/') else ''
                    )
                    self.routes.append((url, view))
            for handler in getattr(package, 'handlers', []):
                if hasattr(handler, 'event'):
                    event = r'{0}/{1}'.format(package.name, handler.event)
                    self.events[event] = handler
            # TODO: add FormBehaviour parsing
