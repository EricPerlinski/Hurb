##########################################################################################
####		BASIC IMPORT 
##########################################################################################

import os
import random
import datetime
from google.appengine.api import memcache

##########################################################################################
####		WEB RELATIVES IMPORT AND CONFIGURATIONS
##########################################################################################

import webapp2
import jinja2
import json

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


##########################################################################################
####        CACHE SYSTEM 
##########################################################################################


def getAllTasks(update = False):
    key = 'tasks'
    tasks = memcache.get(key)
    if tasks is None or update:
        tasks = db.GqlQuery('Select * from Task')
        tasks = list(tasks)
        memcache.set(key, tasks)        
    return tasks


def getCommentsOfTasks(task_id, update = False):
    key = task_id
    comments = memcache.get(key)
    if comments is None or update:
        comments = db.GqlQuery('Select * from Comment where task_id = :1 ORDER BY date DESC', int(key) )       
        comments = list(comments)
        memcache.set(key, comments)
        return comments, True
    return comments, False

def getTaskByKey(task_id):
    key = db.Key.from_path('Task',int(task_id), parent = task_key())
    task = db.get(key)
    if task:
        return task 
    return None

##########################################################################################
####        DB ACCESS   -   TASK PROCESS
##########################################################################################

def putTaskInCache(task):
    key = 'tasks'
    tasks = memcache.get(key)
    if tasks :
        tasks.append(task)
    else:
        tasks = []
        tasks.append(task)

    memcache.delete(key)
    memcache.set(key, tasks)        

def participateToTask(task_id, username):    
    key = db.Key.from_path('Task',int(task_id), parent = task_key())
    task = db.get(key)   
    #If the task exists, add the user as a participant
    if task is not None:        
        task.addParticipant(int(task_id), username)
        # update the cache
        key = 'tasks'
        tasks = memcache.get(key)
        for c in tasks:
            if c.__eq__(task):
                index = tasks.index(c)
                tasks[index] = task
                break
        if not memcache.set(key, tasks):            
            memcache.delete(key)
            memcache.set(key, tasks)
        
        return True
    else:
        return False

def cancelParticipation(task_id, username):
    task = getTaskByKey(task_id)
    if not task:
        return False
    participants = task.getParticipant(task_id)    
    if participants is not None and username in participants:
        task.participants.remove(username)
        # update the cache
        key = 'tasks'
        tasks = memcache.get(key)
        for c in tasks:
            if c.__eq__(task):
                index = tasks.index(c)
                tasks[index] = task                               
                break
        if not memcache.set(key, tasks):            
            memcache.delete(key)
            memcache.set(key, tasks)                  
        task.put()
          
        return True
    return False


def deleteTask(task_id, username):
    if task_id and username:         
        key = db.Key.from_path('Task',int(task_id), parent = task_key())
        task = db.get(key)  
        #Get the username of the creator
        if task is not None:                
            creator = task.author;
            if username == creator:
                #Delete entry in cache
                key = 'tasks'
                tasks = memcache.get(key)

                found = False
                for c in tasks:
                    if c.__eq__(task):
                        tasks.remove(task)
                        found = True
                        break
                if not found :
                    return list('notFound !!!'), False
                
                memcache.delete(key)
                if not memcache.set(key, tasks):            
                    memcache.delete(key)
                    memcache.set(key, tasks)
                
                task.delete()
                #Delete all comments relative to the Task        
                taskComments = Comment.all()
                taskComments.filter("task_id =", task_id)
                for comment in taskComments.run():
                    comment.delete()

                return memcache.get(key), True
            else:
                return list('notasks'), False
    else:
        return list('notasks'), False




##########################################################################################
####        DB ACCESS   -   COMMENT PROCESS
##########################################################################################

def commentTask(task_id, author, content):
    if task_id and content :
        com = Comment(task_id = int(task_id), author = author, content = content, date = datetime.datetime.now())
        com.put()      
        # Update the cache
        if com :
            comments = memcache.get(task_id)
            if comments :
                comments.append(com)
                memcache.set(task_id, comments)
            else:
                comments = []
                comments.append(com)
                memcache.set(task_id, comments)

            
            return True
        else:
            return False
    else:
        return False

def deleteComment(task_id, comment_id):
    key_comment = db.Key.from_path('Comment', int(comment_id))
    commentToDel = db.get(key_comment)
    if commentToDel:
        #Delete entry in the cache
        comments = memcache.get(task_id)
        if len(comments) == 0:
            pass
        elif len(comments) == 1:
            comments.pop(0)
        else:
            for c in comments:
                if c.__eq__(commentToDel):
                    index = comments.index(c)
                    comments.pop(index)            
                    break
        
        memcache.set(task_id, comments) 
        commentToDel.delete()
         

        return memcache.get(task_id), True
    return list('nocomment'), False





class HurbHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render_json(self,d):
        json_txt = json.dumps(d)
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(json_txt)

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

        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'


class Main(HurbHandler):
    def get(self):
        if self.format == 'html':
            tasks = getAllTasks() 
            if self.user:
                 self.render('home.html', tasks = tasks, username = self.user.username)
            else:
              errorlog="you need to be logged in =/"
              self.response.out.write(self.request.get('errorlog'))
              if self.request.get('errorlog'):  
                 self.render('home.html', tasks = tasks,errorlog=errorlog)
              else:
                 self.render('home.html', tasks = tasks)
        else:
            tasks = Task.all().order('-date')
            return self.render_json([t.as_dict() for t in tasks])

    def post(self):
        
        self.comment = self.request.get('commentSend')
        self.content = self.request.get('commentContent')     
        self.task_id = self.request.get('task_id')
        self.delete = self.request.get('deleteTask')
        self.participate = self.request.get('participateTask')
        self.cancel = self.request.get('cancelParticipation')

        if self.user: 
            error = False
            error_log = ""

            #comment the Task
            if self.comment :
                if not commentTask(self.task_id, self.user.username, self.content):   
                    error = True             
                    error_log = "Comment has not been saved"
                
            #Delete the task with its comments        
            if self.delete :
                tasks, status = deleteTask(self.task_id, self.user.username)
                if status:
                    self.redirect('/')
                else:
                    self.redirect('/', None)

            #participate to the task
            if self.participate :            
                if not participateToTask(self.task_id, self.user.username):                
                    error = True
                    error_log = "Task doesn't exist anymore"
            
            #Leave a task:
            if self.cancel: 
                if not cancelParticipation(self.task_id, self.user.username):
                    error = True
                    error_log = "Participation canceled not handled"


            # tasks = getAllTasks(True)
            # comments = getAllComments(True)
            if error :
                self.response.out.write("error log : "+error_log)
            else:            
                self.redirect('/') 
        else:
            # tasks = getAllTasks(True)
            # comments = getAllComments(True)
            
            self.render('home.html',tasks = tasks, comments = comments,errorlog=errorlog)
                   


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
        task = getTaskByKey(task_id)
        if not task:
            self.error(404)
            return

        tasks = getAllTasks(True)                
        comments, status = getCommentsOfTasks(task_id)

        if self.format == 'html':
            if self.user:
                self.render("taskpermalink.html", task=task, username = self.user.username, comments = comments)
            else:
                self.render("taskpermalink.html", task=task, username = "", comments = comments)
                #self.response.out.write("GET : no user")   
        else:
            self.render_json(task.as_dict())


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


        if self.user:
            error_log = ""
            error = False

            task = getTaskByKey(task_id)
            if not task:
                self.error(404)
                return

            #comment the Task
            if self.comment :
                if not commentTask(task_id, self.user.username, self.content):                
                    error_log = "Comment has not been saved"
                    error = True
            
            #Delete the task with its comments        
            if self.delete :
                tasks, status = deleteTask(self.task_id, self.user.username)            
                if status:
                    redirectTo = "/"
                    # error_log = "delete task correct "
                    # for t in tasks :
                    #     error_log = error_log + t.title + " - "
                    # error = True
                    #self.redirect('/', tasks)
                    #self.redirect('/')
                else:
                    error_log = "delete task NOT correct "
                    for t in tasks :
                        error_log = error_log + t + " - "
                    error = True
                    # self.redirect('/', None)

            #delete a comment
            if self.deleteComment:
                if self.deleteComment:
                    comments, status = deleteComment(task_id, self.comment_id)
                    if not status:
                        error = True
                        error_log = "Fail to delete comment"


            #participate to the task
            if self.participate :            
                if not participateToTask(task_id, self.user.username):                
                    error_log = "Task doesn't exist anymore"
                    error = True

            #Leave a task:
            if self.cancel: 
                if not cancelParticipation(task_id, self.user.username):
                    error_log = "Cannot cancel participation"
                    error = True

            if error :
                self.response.out.write("Error : "+error_log)
            else:
                self.redirect(redirectTo)
        else:
            tasks = getAllTasks(True)
            
            self.redirect('/?errorlog=1')


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
        if self.format == 'json':
            user = Bro.by_name(username)
            self.render_json(user.as_dict())
        else:
            if self.user and self.user.username == username:
                self.redirect("/profil")
            else:            
                dateminusoneweek = datetime.datetime.now() - datetime.timedelta(days=7) 
                task = db.GqlQuery("Select * from Task")
                UserTask = Task.GiveUserTask(username)   #on doit egalement faire une veriification sur le nom de l'user
                participant=[]
                for t in task:
                    if t.getParticipate(username):
                        participant.append(t)
                email=Bro.by_name(username).email
                self.render("information.html",mail=email,username=username,UserTask=UserTask,participant=participant)
                    

            #self.render("taskpermalink.html", task=task, username = self.user.username, comments = comments)


class Tasks(HurbHandler):
    def get(self):
        tasks = Task.all().order('-date')
        if self.format == 'html':
            self.redirect('/')
        else:
            return self.render_json([t.as_dict() for t in tasks])


class Profil(HurbHandler):
    def get(self):
        if self.user :
            if self.format == 'json':
                user = Bro.by_name(self.user.username)
                self.render_json(user.as_dict_profil())
            else:
                UserTask=Task.GiveUserTask(self.user.username)
                task = db.GqlQuery("Select * from Task")
                participant=[]
                for t in task:
                    if t.getParticipate(self.user.username):
                        participant.append(t)
                a=Task.GiveUserTask(self.user.username)
                self.render('profil.html', user = self.user, username = self.user.username, profil = "profil",a=a,UserTask=UserTask,participant=participant)
        else:
            self.redirect('/login')

    
class Contact(HurbHandler):
    def get(self):
        if self.user :
            self.render('contact.html', user = self.user, username = self.user.username)
        else:
            self.render('contact.html')

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
        if self.user :
            broName = self.user.username
            #get all tasks created by the bro
            taskCreated = Task.GiveUserTask(broName)
            for t in taskCreated:
                deleteTask(str(t.key().id()), broName)

            # get each comment published by the bro and delete them
            comments = db.GqlQuery("Select * from Comment where author =:1", broName)
            for c in comments:
                c.delete()
                getCommentsOfTasks(str(t.key().id()), True)

            # get all tasks in which the bro participates
            tasks = db.GqlQuery("Select * from Task")
            taskParticipation = []
            for t in tasks:
                if t.getParticipate(broName):
                    taskParticipation.append(t)
                cancelParticipation(str(t.key().id()), broName)
           

            getAllTasks(True)
            Bro.Deleted(self.user.username)
            self.user = None

        self.redirect('/')
        

application = webapp2.WSGIApplication([('/(?:.json)?',Main),
									   ('/profil(?:.json)?',Profil),
                                       ('/delete',Delete),
                                       ('/login',Login),
                                       ('/tasks(?:.json)?',Tasks),
                                       ('/task/([0-9]+)(?:.json)?', TaskPage),
                                       ('/logout', Logout), 
                                       ('/contact', Contact),
                                       ('/user/([0-9a-zA-Z]+)(?:.json)?', UserPage),
                                       ('/signup',SaveUser),
                                       ('/newtask', NewTask),
                                       ('/profil/modify', Modify)],
                                      debug=True)