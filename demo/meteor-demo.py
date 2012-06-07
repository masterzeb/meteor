#!/usr/bin/python3

# it's temporary until setup.py will be written
import sys
sys.path.append('/home/ziberbulger/sources/diploma')

from meteor.core import Application
from meteor.utils import parse_args
from meteor.handlers import WSConnection

import time


class ChatWSConnection(WSConnection):
    def get_current_user(self):
        user = self.get_secure_cookie('username', None)
        return user.decode('utf-8') if user else None

    def open(self):
        if self.current_user:
            self.db.messages.create(
                user=self.current_user, content='joined the chat',
                timestamp=int(time.time()), system=True
            )
            self.broadcast('user_enter', {'user': self.current_user})
            super(ChatWSConnection, self).open()

    def on_close(self):
        super(ChatWSConnection, self).on_close()
        self.db.messages.create(
            user=self.current_user, content='left the chat',
            timestamp=int(time.time()), system=True
        )
        self.broadcast('user_leave', {'user': self.current_user})


@parse_args
def main():
    Application(ws_connection=ChatWSConnection).run()

if __name__ == '__main__':
    main()
