from meteor.handlers import EventHandler

import time


class NewMessageEvent(EventHandler):
    event = 'new_message'

    def handling(self, data):
        self.db.messages.create(user=self.current_user,
            content=data['msg'], timestamp=int(time.time()))

        self.broadcast(event=self.event_fullname,
            data={'user': self.current_user, 'msg': data['msg']})
