from meteor.core import EventHandler

class TestHandler(EventHandler):
    event = 'test'

    def execute(self, data):
        self.send(data)