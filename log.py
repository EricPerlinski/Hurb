import os
import re
import random
import hashlib
import hmac
import logging
import json
from string import letters

import webapp2
import jinja2

from google.appengine.ext import db
import datetime

template_dir= os.path.join(os.path.dirname(__file__),'templates');
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True);


secret = 'Dunno'


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

PHONE_RE = re.compile(r".*?(\(?\d{3}\D{0,3}\d{3}\D{0,3}\d{4}).*?")
def valid_phone(phone):
    return not phone or PHONE_RE.match(phone)

ADDRESS_RE = re.compile(r"[a-zA-Z0-9\.\-\,]+")
def valid_address(address):
    return not address or ADDRESS_RE.match(address)


class BlogHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        
        t = jinja_env.get_template(template)
        return t.render(params)

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

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and Register.by_id(int(uid))


        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'htlm'


#### TODO ##################################################################
#### Modify this in order to get the correct user pattern you've defined####
############################################################################


class Register(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
    email = db.StringProperty()
    phone = db.StringProperty()
    address = db.StringProperty()
    @classmethod
    def by_id(cls, uid):
        return Register.get_by_id(uid, parent = register_key())

    @classmethod
    def by_name(cls, name):
        u = Register.all().filter('username =', name).get()
        return u

    @classmethod
    def register(cls, username, password, email,phone,address):
        pw_hash = make_pw_hash(username, password)
        return Register(parent = register_key(),
                    username = username,
                    password = pw_hash,
                    email = email,
                    phone=phone,
                    address=address)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.password):
            return u

def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def register_key(name = 'default'):
    return db.Key.from_path('register', name)


###### TODO ####################################################################
###### Modify this in order to get the correct post pattern you've defined #####
################################################################################
def task_key(title = 'default'):
        return db.Key.from_path('task', title)

class Task(db.Model):
    author = db.StringProperty(required = True)
    title = db.StringProperty(required = True)
    description = db.TextProperty(required = True)
    #Both date and time will be in this field
    date = db.DateTimeProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return Task.get_by_id(uid, parent = register_key())

    @classmethod
    def by_name(cls, name):
        u = Task.all().filter('title =', name).get()
        return u

    @classmethod
    def register(cls, ):
        pw_hash = make_pw_hash(username, title, description, date,time)
        return Task(parent = task_key(),
                    title = title,
                    description = description,
                    date = date,
                    time = time
                    )

    def render(self):
        self._render_text = self.description.replace('\n', '<br>')
        return render_str("task.html", task = self)

    def as_dict(self):
        time_fmt = '%d-%m-%Y %H:%M'
        d = {'title': self.title,
             'description': self.description,
             'date': self.date.strptime(date+" "+time,time_fmt)


            }
        return d

    

class NewTask(BlogHandler):
    def get(self):
        self.render('newtask.html')

    def post(self):
        have_error = False
        self.author = self.user.username
        self.taskTitle = self.request.get('title')
        self.taskDescription = self.request.get('description')
        self.taskDate = self.request.get('date')


        params = dict(title = self.taskTitle,
                      description = self.taskDescription,
                      date = self.taskDate)


        if not self.taskTitle:
            params['error_title'] = "Please enter a Title"
            have_error = True

        if not self.taskDescription:
            params['error_description'] = "Please enter a description"
            have_error = True            

        #Check the date, cannot be a previous date
        if not self.taskDate:
            params['error_date'] = "Please, set up a date"
            have_error = True
        else:
            #Validate the date
            convertedDate = self.changeToDate(self.taskDate)            
            have_error = not self.validateDate(convertedDate)

            if have_error :
                params['error_date'] = "Choosen Date is not valid"
            

        #Add the new task if it doesn't have any error
        if have_error:
            self.render('newtask.html', **params)
        else:
            #self.write(self.taskDate)
            task = Task(parent = task_key(), author = self.author, title = self.taskTitle, description = self.taskDescription, date = convertedDate)
            task.put()
            params['valid_task'] = "Your task has been added to the taskBoard"


    def changeToDate(self, taskDate):
        #####
        #Convert the given date to a dateTime object
        #####
        #Split the dd/mm/yyyy HH:ii P in two pieces        
        self.dateAndtime = self.taskDate.split(' ', 1)

        self.dateString = self.dateAndtime[0].split('/', 2)       

        self.timeString = self.dateAndtime[1].split(' ', 2) #P argument is included
        self.time = self.timeString[0].split(':', 1)

        #Convert the format hour, according to the P parameter:
        #transpose it to integer anyway
        format = self.timeString[1]
        if format == 'PM':
            self.hour = int(self.time[0])+12
        else:
            self.hour = int(self.time[0])


        self.date = datetime.datetime(year=int(self.dateString[2]), 
                                month=int(self.dateString[1]),
                                day=int(self.dateString[0]),
                                hour=self.hour,
                                minute=int(self.time[1]))

        return self.date


    def validateDate(self, taskDate):
        if taskDate < datetime.datetime.now():
            return False

        return True





class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=blog_key())
        post = db.get(key)

        if not post:
            self.error(404)
            return
        if self.format == 'html':
            self.render("permalink.html", post = post)
        else:
            self.render_json(post.as_dict())

class NewPost(BlogHandler):
    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/signup')

        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            p = Post(parent = blog_key(), subject = subject, content = content)
            p.put()
            self.redirect('/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)

class Main(BlogHandler):
    def get(self):
        if self.user:     
            

            tasks = Task.all()
            if tasks:
                self.render('task.html', tasks = tasks)
            else:
                self.render('home.html', user = self.user)
            
        else:
            self.render('home.html')

class BlogFront(BlogHandler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        if self.format == 'html':
            
            self.render('front.html', posts = posts)
        else:
            return self.render_json([p.as_dict() for p in posts])


class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')
        self.phone = self.request.get('phone')
        self.address = self.request.get('address')

        params = dict(username = self.username,
                      email = self.email,
                      phone=self.phone,
                      address=self.address)

        #verifier dans la base que pseudo n'existe pas
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

        if not valid_phone(self.phone):
        	params['error_phone']="That's not a valid phone number"
        	have_error = True

        if not valid_address(self.address):
            params['error_address'] = "It doesn't seems to make sense."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError


class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = Register.login(username,password)
        if u:
            self.login(u)
            self.redirect('/')
        else: 
            msg = 'Invalid login'
            self.render('login-form.html',error = msg)


class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class SaveUser(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = Register.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = Register.register(self.username, self.password,self.email,self.phone,self.address)
            u.put()
            self.login(u)
            self.redirect('/profil')

class Profil(BlogHandler):
	def get(self):
		if self.user :
			self.render('profil.html',user = self.user)
		else:
			self.redirect('/login')



application = webapp2.WSGIApplication([('/',Main),
									   ('/profil',Profil),
                                       ('/login',Login),
                                       ('/?(?:.json)?', BlogFront),
                                       ('/([0-9]+)(?:.json)?', PostPage),
                                       ('/logout', Logout),
                                       ('/signup',SaveUser),
                                       ('/newtask', NewTask)],
                                      debug=True)
