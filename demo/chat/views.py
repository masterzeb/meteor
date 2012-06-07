from meteor.handlers import View
from tornado.web import authenticated

class ChatView(View):
    url = '/'

    def get_current_user(self):
        return self.get_secure_cookie('username', None)

    @authenticated
    def get(self):
        # get other users count
        count = len(self.application.ws_connection.users)
        if self.current_user in [c.current_user \
            for c in self.application.ws_connection.users]:
                count -= 1

        # get history
        history = self.db.messages.all.sort('timestamp').limit(50).data
        self.render_view('index.html', history=history, count=count)
