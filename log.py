import os
import webapp2
import jinja2
import re

template_dir= os.path.join(os.path.dirname(__file__),'templates');
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True);


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)


class BlogHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)


    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))


    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')



class Main(BlogHandler):
    def get(self):
        self.render("home.html")



class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            """Ecrire dans la base de donnee"""
            self.redirect('/newcomer')


class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        """
         lire la base de donnee pour verifier que l'utilisateur existe 
        """


class Newcomer(BlogHandler):
    def get(self):
        self.render('newcomer.html')




class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/signup')


application = webapp2.WSGIApplication([('/',Main),
                                       ('/login',Login),
                                       ('/logout', Logout),
                                       ('/signup',Signup),
                                       ('/newcomer',Newcomer),],
                                      debug=True)
