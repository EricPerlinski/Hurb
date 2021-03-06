##########################################################################################
####		MODULE : Task.py
##########################################################################################
from google.appengine.ext import db
from security import make_pw_hash

import os
import jinja2

template_dir= os.path.join(os.path.dirname(__file__),'templates');
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True);

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)



##########################################################################
###### 		Comment class
##########################################################################      
class Comment(db.Model):
    task_id = db.IntegerProperty(required = True)
    author = db.StringProperty(required = True)
    content = db.StringProperty(required = True, multiline = True )
    date = db.DateTimeProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return Comment.get_by_id(uid, parent = register_key())

    @classmethod
    def by_taskid(cls, taskid):
        u = Comment.all().filter('task_id =', taskid).get()
        return u   

    def gettaskid(self):
        return self.task_id

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("comment.html", comment = self)

    def as_dict(self):
        time_fmt = '%d-%m-%Y %H:%M'
        d = {'author' : self.author,
        	 'content': self.content,
             'date-content': self.date.strftime(time_fmt)
            }
        return d

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__


##########################################################################
###### 		Task class
##########################################################################
def task_key(title = 'default'):
        return db.Key.from_path('task', title)

class Task(db.Model):
    author = db.StringProperty(required = True)
    title = db.StringProperty(required = True)
    description = db.StringProperty(required = True, multiline = True)    
    date = db.DateTimeProperty(required = True) #Both date and time will be in this field    
    participants = db.StringListProperty()		#Save the username of all users who wants to participate
    location_lat = db.FloatProperty(required = True)
    location_lng = db.FloatProperty(required = True)
    reward = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return Task.get_by_id(uid, parent = register_key())

    @classmethod
    def by_name(cls, name):
        u = Task.all().filter('title =', name).get()
        return u

    def render(self, username):
        self._render_text = self.description.replace('\n', '<br>')
        return render_str("task.html", t = self, username = username)

    def getNumberOfComments(self,jinjaid):
        comments = Comment.all()
        count = 0
        for i in comments:
            if i.gettaskid() == jinjaid:
                count = count+1
        return count


    def getComments(self):
        comments = []
        comment = Comment.all()
        count = 0
        for i in comment:
            if i.gettaskid() == self.key().id():
                comments.append(i.as_dict())
        return comments

    @classmethod
    def getNumberOfParticipants(self, jinjaid):
        key = db.Key.from_path('Task',int (jinjaid), parent = task_key())            
        task = db.get(key)
        if task != None:
            return len(task.participants)
        else:
            return 0
    
    def as_dict(self):
        time_fmt = '%d-%m-%Y %H:%M'
        d = {'title': self.title,
             'description': self.description,
             'date-event': self.date.strftime(time_fmt),
             'author' : self.author,
             'location_lat' : self.location_lat,
             'location_lng' : self.location_lng,
             'participants' : self.participants,
             'reward' : self.reward,
             'comments' : self.getComments()
        }
        return d

    @classmethod
    def GiveUserTask(cls,username):
        TaskUser= db.GqlQuery('Select * from Task where author= :1',username)
        return TaskUser.run()

    def getParticipant(cls,task_id):
        key = db.Key.from_path('Task', int(task_id), parent = task_key())
        task = db.get(key)
        if task != None :
            return task.participants
        else:
            return None

    def getParticipate(self,username):
        for t in self.participants:
            if t == username:
                return True
        return False


    def addParticipant(cls, task_id, username):
        key = db.Key.from_path('Task',int (task_id), parent = task_key())            
        task = db.get(key)        
        if username not in task.participants:
            task.participants.append(username)
            task.put()

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other): 
        return self.__dict__ == other.__dict__

    






