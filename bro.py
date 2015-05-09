##########################################################################################
####		MODULE : Bro.py
##########################################################################################
from google.appengine.ext import db
from security import make_pw_hash
from security import valid_pw


def bro_key(name = 'default'):
    return db.Key.from_path('bro', name)


class Bro(db.Model):
    username = db.StringProperty(required = True)
    password = db.StringProperty(required = True)
    email = db.StringProperty()
    phone = db.StringProperty()
    address = db.StringProperty()
    @classmethod
    def by_id(cls, uid):
        return Bro.get_by_id(uid, parent = bro_key())

    @classmethod
    def by_name(cls, name):
        u = Bro.all().filter('username =', name).get()
        return u

    @classmethod
    def register(cls, username, password, email,phone,address):
        pw_hash = make_pw_hash(username, password)
        return Bro(parent = bro_key(),
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

    @classmethod
    def update(cls,user,newusername,newpassord,newemail,newphone,newaddress):
        OldUsername=user.username
        ListUser= db.GqlQuery('Select * from Bro where username= :1',OldUsername)
        result=ListUser.get()
        setattr(result,'username',newusername)
        user.username=newusername
        setattr(result,'password',make_pw_hash(newusername,newpassord))
        user.password=make_pw_hash(newusername,newpassord)
        setattr(result,'email',newemail)
        user.email=newemail
        setattr(result,'phone',newphone)
        user.phone=newphone
        setattr(result,'address',newaddress)
        user.adrdress=newaddress
        result.put()
        TaskAuthor= db.GqlQuery('Select * from Task where author= :1',OldUsername)
        results=TaskAuthor.run()
        for result in results:
            setattr(result,'author',newusername)
            result.put()

    @classmethod
    def Deleted(cls,usern):
        userToDeleted = db.GqlQuery('Select * from Bro where username=:1',usern)
        if userToDeleted :
          userToDeleted[0].delete()
