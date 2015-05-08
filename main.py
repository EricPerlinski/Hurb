##########################################################################################
####		BASIC IMPORT 
##########################################################################################

import os
import random
import datetime

##########################################################################################
####		WEB RELATIVES IMPORT AND CONFIGURATIONS
##########################################################################################

import webapp2
import jinja2
template_dir= os.path.join(os.path.dirname(__file__),'templates');
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True);
def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


##########################################################################################
####		MODULES IMPORT
##########################################################################################
from security import *
from bro import *
from task import *

def validDate(taskDate):
    return (datetime.datetime.now() < taskDate)


def changeToDate(taskDate):    
    #Convert the given date (dd/mm/yyyy HH:ii P) to a dateTime object          
    dateAndtime = taskDate.split(' ', 1)
    dateString = dateAndtime[0].split('/', 2)       
    timeString = dateAndtime[1].split(' ', 2) #P argument is included
    time = timeString[0].split(':', 1)
    hour = int(time[0])

    format = timeString[1]
    if format == 'PM':
        hour = hour+12
    
    date = datetime.datetime(year=int(dateString[2]), 
                            month=int(dateString[1]),
                            day=int(dateString[0]),
                            hour=hour,
                            minute=int(time[1]))

    return date



class HurbHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

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
        self.user = uid and Bro.by_id(int(uid))


class Main(HurbHandler):
    def get(self):
        if self.user:     
            tasks = Task.all()
            self.render('home.html', tasks = tasks)            
        else:
            self.render('home.html')

    def post(self):
        self.comment = self.request.get('commentSend')
        self.content = self.request.get('commentContent')        
        self.task_id = self.request.get('task_id')


        if self.comment and self.content and self.task_id:
            com = Comment(task_id = int(self.task_id), author = self.user.username, content = self.content, date = datetime.datetime.now())
            com.put()        
            self.response.out.write("Comm enregistre")

        self.response.out.write("Comm saute\n")
        self.response.out.write("com: "+self.comment+"\n")   
        self.response.out.write("content :"+self.content+"\n")   
        self.response.out.write("task :"+self.task_id)   
        self.render('header.html');



class NewTask(HurbHandler):
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
                      date = self.taskDate,
                      author = self.author)


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
            convertedDate = changeToDate(self.taskDate)            
            have_error = not validDate(convertedDate)

            if have_error :
                params['error_date'] = "Choosen Date is not valid"
        

        #Add the new task if it doesn't have any error
        if have_error:
            self.render('newtask.html', **params)
        else:
            #self.write(self.taskDate)
            task = Task(parent = task_key(), author = self.author, title = self.taskTitle, description = self.taskDescription, date = convertedDate)
            task.put()
            self.redirect('/task/%s' % str(task.key().id())) 


class TaskPage(HurbHandler):
    def get(self,task_id):
        key = db.Key.from_path('Task',int (task_id), parent = task_key())
        task = db.get(key)

        if not task:
            self.error(404)
            return

        self.render("taskpermalink.html", task=task)

    def post(self, task_id):
        self.comment = self.request.get('comment')
        self.delete = self.request.get('delete')


        key = db.Key.from_path('Task',int (task_id), parent = task_key())
        task = db.get(key)
        if not task:
            self.error(404)
            return


        #Leave a comment :
        if self.comment:
            com = Comment(task_id = int(task_id), author = self.user.username, content = "Just a comment test", date = datetime.datetime.now())
            com.put()
            self.render("taskpermalink.html", task = task, comment=com)

        #Participate to the task
        elif self.delete:
            task.delete()            
            self.redirect('/')

        else:
            self.render("header.html", task = task)   

class Signup(HurbHandler):
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


class Login(HurbHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = Bro.login(username,password)
        if u:
            self.login(u)
            self.redirect('/')
        else: 
            msg = 'Invalid login'
            self.render('login-form.html',error = msg)


class Logout(HurbHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class SaveUser(Signup):
    def done(self):
        #make sure the user doesn't already exist
        u = Bro.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = Bro.register(self.username, self.password,self.email,self.phone,self.address)
            u.put()
            self.login(u)
            self.redirect('/profil')

class Profil(HurbHandler):
    def get(self):
        if self.user :
            UserTask=Task.GiveUserTask(self.user.username)
            self.render('profil.html', user = self.user, profil = "profil",UserTask=UserTask)
        else:
            self.redirect('/login')

class Modify (Signup):
    def get (self):
        if self.user:
            self.render('signup-form.html',user = self.user)
        else :
            self.redirect('/login')

    def done(self):
        if self.user:
            u = Bro.by_name(self.username)
            if u:
                msg = 'That user already exists.'
                self.render('signup-form.html', error_username = msg)
            else:
                self.user.update(self.user,self.username,self.password,self.email,self.phone,self.address)
                UserTask=Task.GiveUserTask(self.user.username)
                self.render('profil.html', user = self.user, profil = "profil",UserTask=UserTask)
        else :
            self.redirect('/login')




application = webapp2.WSGIApplication([('/',Main),
									   ('/profil',Profil),
                                       ('/login',Login),
                                       ('/task/([0-9]+)(?:.json)?', TaskPage),
                                       ('/logout', Logout),
                                       ('/signup',SaveUser),
                                       ('/newtask', NewTask),
                                       ('/profil/modify', Modify)],
                                      debug=True)