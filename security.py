##########################################################################################
####		MODULE : SECURITY.py
##########################################################################################


import re
import random
import hashlib
import hmac
from string import letters



secret = 'Dunno'
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
PASS_RE = re.compile(r"^.{3,20}$")
EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
PHONE_RE = re.compile(r".*?(\(?\d{3}\D{0,3}\d{3}\D{0,3}\d{4}).*?")
ADDRESS_RE = re.compile(r"[a-zA-Z0-9\.\-\,]+")

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def valid_username(username):
    return username and USER_RE.match(username)


def valid_password(password):
    return password and PASS_RE.match(password)


def valid_email(email):
    return not email or EMAIL_RE.match(email)


def valid_phone(phone):
    return not phone or PHONE_RE.match(phone)


def valid_address(address):
    return not address or ADDRESS_RE.match(address)

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

