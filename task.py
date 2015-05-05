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
    content = db.StringProperty(required = True)
    date = db.DateTimeProperty(required = True)    

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("comment.html", comment = self)

    def as_dict(self):
        time_fmt = '%d-%m-%Y %H:%M'
        d = {'task_id': self.task_id,
        	 'author' : self.author,
        	 'content': self.content,
             'date': self.date.strftime(time_fmt)
            }
        return d


##########################################################################
###### 		Task class
##########################################################################
def task_key(title = 'default'):
        return db.Key.from_path('task', title)

class Task(db.Model):
    author = db.StringProperty(required = True)
    title = db.StringProperty(required = True)
    description = db.TextProperty(required = True)    
    date = db.DateTimeProperty(required = True) #Both date and time will be in this field    
    participants = db.ListProperty(int)			#Save the id of all users who wants to participate

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
                    date = date
                    )

    def render(self):
        self._render_text = self.description.replace('\n', '<br>')
        return render_str("task.html", t = self)


    def as_dict(self):
        time_fmt = '%d-%m-%Y %H:%M'
        d = {'title': self.title,
             'description': self.description,
             'date': self.date.strftime(time_fmt),
             'author' : self.author
            }
        return d



