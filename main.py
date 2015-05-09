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


def commentTask(task_id, author, content):
    if task_id and content :
        com = Comment(task_id = int(task_id), author = author, content = content, date = datetime.datetime.now())
        com.put()        
        return True
    else:
        return False

def deleteTask(task_id, username):
    if task_id and username:
        key = db.Key.from_path('Task',int (task_id), parent = task_key())            
        task = db.get(key)
        #Get the username of the creator 
        if task is not None:                
            creator = task.author;
            if username == creator:
                task.deleteComments(int(task_id))
                task.delete()
                return (True, "Task has been correctly deleted")
            else:
                return (False, "You cannot delete tasks from other Bros modafucka !!!")
    else:
        return (False, "Task has not been deleted : data are missing")

def participateToTask(task_id, username):
    key = db.Key.from_path('Task',int (task_id), parent = task_key())            
    task = db.get(key)
    #If the task exists, add the user as a participant
    if task is not None:                                
        task.addParticipant(int(task_id), username)
        return True
    else:
        return False


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
        self.response.out.write("getMainPage")
        if self.user:   
            tasks = Task.all()            
            self.render('home.html', tasks = tasks, username = self.user.username)            
        else:
            tasks = Task.all()
            self.render('home.html',tasks = tasks)

    def post(self):
        self.response.out.write("postMainPage")
        self.comment = self.request.get('commentSend')
        self.content = self.request.get('commentContent')     
        self.task_id = self.request.get('task_id')
        self.delete = self.request.get('deleteTask')
        self.participate = self.request.get('participateTask')
        self.cancel = self.request.get('cancelParticipation')

        #comment the Task
        if self.comment :
            if not commentTask(self.task_id, self.user.username, self.content):                
                self.response.out.write("Comment has not been saved")
            else:
                self.redirect('/')

        #Delete the task with its comments
        if self.delete :
            status,msg = deleteTask(self.task_id, self.user.username)
            if not status:                
                self.response.out.write("%s" % msg)
            else:
                self.response.out.write("%s" % msg)
                self.redirect('/')

        #participate to the task
        if self.participate :
            #self.response.out.write("You really want to participate !!!")
            if not participateToTask(self.task_id, self.user.username):                
                self.response.out.write("Task doesn't exist anymore")
            else:
                self.redirect('/')

        #Leave a task:
        if self.cancel:
            key = db.Key.from_path('Task',int (self.task_id), parent = task_key())
            self.task = db.get(key)
            if not self.task:
                self.error(404)
                return
            #Is the user
            participants = self.task.getParticipant(self.task_id)
            #task.getNumberOfParticipants(self.task_id) > 0 
            if participants is not None and self.user.username in participants:                
                self.task.participants.remove(self.user.username)
                self.task.put()
            self.redirect('/')


        tasks = Task.all()
        comments = Comment.all()
        self.render('home.html', tasks = tasks, comments = comments)



class NewTask(HurbHandler):
    def get(self):
        self.render('newtask.html')

    def post(self):
        have_error = False
        self.author = self.user.username
        self.taskTitle = self.request.get('title')
        self.taskDescription = self.request.get('description')
        self.taskDate = self.request.get('date')
        self.location_lat = float(self.request.get('location_lat'))
        self.location_lng = float(self.request.get('location_lng'))
        self.reward = self.request.get('reward')

        params = dict(title = self.taskTitle,
                      description = self.taskDescription,
                      date = self.taskDate,
                      author = self.author,
                      location_lat = self.location_lat,
                      location_lng = self.location_lng,
                      reward = self.reward)

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
        
        if not self.location_lat or not self.location_lng:
            params['error_map'] = "You didn't choose any location ! : current lat : "+self.location_lat + " - current lng : "+self.location_lng
            have_error = True


        #Add the new task if it doesn't have any error
        if have_error:
            self.render('newtask.html', **params)
        else:
            
            task = Task(parent = task_key(), author = self.author, title = self.taskTitle, description = self.taskDescription, date = convertedDate, location_lat = self.location_lat, location_lng = self.location_lng, reward = self.reward, participants = [])

            task.put()
            self.redirect('/task/%s' % str(task.key().id())) 


class TaskPage(HurbHandler):
    def get(self,task_id):
        key = db.Key.from_path('Task',int (task_id), parent = task_key())
        task = db.get(key)
        comments = Comment.all()
        comments.order('date')        
        if not task:
            self.error(404)
            return

        self.render("taskpermalink.html", task=task, username = self.user.username, comments = comments)

    def post(self, task_id):
        url_get = self.request.url
        id_permalink = url_get.split('/')[4]
        #self.response.out.write("url : "+id_permalink+"  ")
        redirectTo = "/task/"+id_permalink

        self.comment = self.request.get('commentSend')
        self.content = self.request.get('commentContent')        
        self.task_id = self.request.get('task_id')
        self.delete = self.request.get('deleteTask')
        self.participate = self.request.get('participateTask')
        self.cancel = self.request.get('cancelParticipation')
        self.deleteComment = self.request.get('deleteCom')
        self.comment_id = self.request.get('comment_id')

        key = db.Key.from_path('Task',int (self.task_id), parent = task_key())
        self.task = db.get(key)
        if not self.task:
            self.error(404)
            return

        #comment the Task
        if self.comment :
            if not commentTask(self.task_id, self.user.username, self.content):                
                self.response.out.write("Comment has not been saved")
            else:
                self.redirect(redirectTo)

        #Delete the task with its comments
        if self.delete :
            (status,msg) = deleteTask(self.task_id, self.user.username)
            if not status:                
                self.response.out.write("%s" % msg)
            else:
                self.response.out.write("%s" % msg)
                self.redirect(redirectTo)

        if self.deleteComment:
            key_comment = db.Key.from_path('Comment', int(self.comment_id))
            commentToDel = db.get(key_comment)
            commentToDel.delete()
            self.redirect(redirectTo)


        #participate to the task
        if self.participate :
            #self.response.out.write("You really want to participate !!!")
            if not participateToTask(self.task_id, self.user.username):                
                self.response.out.write("Task doesn't exist anymore")
            else:
                self.redirect(redirectTo)
        
        if self.cancel:
            #Is the user
            participants = self.task.getParticipant(self.task_id)
            #task.getNumberOfParticipants(self.task_id) > 0 
            if participants is not None and self.user.username in participants:                
                self.task.participants.remove(self.user.username)
                self.task.put()
            self.redirect(redirectTo)

        comments = Comment.all()
        comments.order('date')   
        self.render("taskpermalink.html", task=self.task, username = self.user.username, comments = comments)
        


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

class UserPage(HurbHandler):
    def get(self,username):
        if self.user.username == username:
            self.redirect("/profil")
        else:
            
            dateminusoneweek = datetime.datetime.now() - datetime.timedelta(days=7) 
            task = db.GqlQuery("Select * from Task")
            tasks = []
            for t in task: 
                if t.getParticipate(username):
                    tasks.append(t.title)
            
            self.response.out.write("Upcomming task : <br/>")
            for i in tasks:
                self.response.out.write( i + "<br/>")
            
                

        #self.render("taskpermalink.html", task=task, username = self.user.username, comments = comments)

    
class Profil(HurbHandler):
    def get(self):
        if self.user :
            UserTask=Task.GiveUserTask(self.user.username)
            self.render('profil.html', user = self.user, username = self.user.username, profil = "profil",UserTask=UserTask)
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

class Delete (HurbHandler):
    def get(self):
        Bro.Deleted(self.user.username)
        self.user=None
        self.redirect('/')

application = webapp2.WSGIApplication([('/',Main),
									   ('/profil',Profil),
                                       ('/delete',Delete),
                                       ('/login',Login),
                                       ('/task/([0-9]+)(?:.json)?', TaskPage),
                                       ('/logout', Logout),
                                       ('/user/([0-9a-zA-Z]+)', UserPage),
                                       ('/signup',SaveUser),
                                       ('/newtask', NewTask),
                                       ('/profil/modify', Modify)],
                                      debug=True)