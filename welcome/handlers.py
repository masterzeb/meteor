from meteor.core import EventHandler

class TestHandler(EventHandler):
    event = 'test'

    def handling(self, data):
        self.send(data)