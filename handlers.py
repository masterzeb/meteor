import inspect
import os
import sys

import tornado.web
import tornado.websocket
import tornado.util

from .template import filters


class WSConnection(tornado.websocket.WebSocketHandler):
    users = set()

    def open(self):
        WSConnection.users.add(self)

    def on_close(self):
        WSConnection.users.remove(self)

    def on_message(self, message):
        data = message.get('data', None)
        if 'cmd' in message:
            handler = self.application.router.commands[message['cmd']](self)
            handler.execute(data)
        elif 'event' in message:
            pass

    @classmethod
    def broadcast(self, criteria=None):
        print(self.users)


class View(tornado.web.RequestHandler):
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
            'scripts': self.application.static_manager.get_chain('js'),
            'css': self.application.static_manager.get_chain('css'),
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

    def send(self, data):
        self.connection.write_message(data)
