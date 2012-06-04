import re
import inspect
import os
import sys

import tornado.web
import tornado.websocket
import tornado.util
from tornado.escape import json_encode, json_decode

from .template import filters


class WSConnection(tornado.websocket.WebSocketHandler):
    users = set()

    def open(self):
        WSConnection.users.add(self)

    def on_close(self):
        WSConnection.users.remove(self)

    def on_message(self, message):
        message = json_decode(message)
        if 'event' in message:
            handler = self.application.router.events[message['event']](self)
            handler.timestamp = message.get('timestamp', None)
            handler.handling(message.get('data', {}))


class View(tornado.web.RequestHandler):
    @property
    def package(self):
        return self.application.package_manager.get_package(self.__class__).name

    def embedded_css(self):
        return ''

    def embedded_js(self):
        return ''

    def get_template_path(self):
        return os.path.join(
            os.path.dirname(sys.modules[self.__module__].__file__), 'templates')

    def prepare(self):
        for name, ref in self.application.databases.items():
            setattr(self, name, ref)

    def render_string(self, *args, **kwargs):
        # add template filters
        global_filters = {}
        for name, obj in inspect.getmembers(filters):
            if isinstance(obj, filters.TemplateFilter):
                global_filters[name] = obj

        # TODO: add custom filters
        kwargs.update(global_filters)
        return super(View, self).render_string(*args, **kwargs)

    def render_view(self, template_name, **kwargs):
        wrapper_path = os.path.realpath(os.path.join(
            os.path.dirname(sys.modules['meteor'].__file__),
            'template', 'view.html'
        ))

        metadata = self.application.views_metadata.copy()
        metadata.update(self.metadata())
        metadata.update({
            'embedded_css': self.embedded_css(),
            'embedded_js': self.embedded_js(),
            'scripts':
                self.application.static_manager.get_chain('js', self.package),
            'css':
                self.application.static_manager.get_chain('css', self.package),
            'minified': self.settings['use_compressed_static']
        })

        wrapper = self.render_string(wrapper_path, **metadata)

        body_index = wrapper.rindex(tornado.util.b('</body>'))
        html = wrapper[:body_index] + \
            self.render_string(template_name, **kwargs) + wrapper[body_index:]
        self.finish(html)

    def metadata(self):
        return {}


class EventHandler(object):
    def __init__(self, connection):
        self.connection = connection
        self.application = connection.application
        # TODO: add more references

    @property
    def package(self):
        return self.application.package_manager.get_package(
            self.__class__, 'handlers').name

    @property
    def event_fullname(self):
        return '/'.join([self.package, self.event])

    def send(self, event, data, **kwargs):
        message = {'event': event, 'data': data}
        message.update(kwargs)
        self.connection.write_message(json_encode(message))

    def answer(self, data, **kwargs):
        if self.timestamp:
            kwargs.update({'timestamp': self.timestamp})
        self.send(self.event_fullname, data, **kwargs)
