from meteor.handlers import View

class AuthView(View):
    url = '/auth'
    
    def get(self):
        if self.get_secure_cookie('username', None):
            self.redirect('/')
        self.render_view('auth.html')

    def post(self):
        username = self.get_argument('username')
        self.set_secure_cookie('username', username)
        self.redirect('/')
