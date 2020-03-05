from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    uid = db.Column(db.Integer, primary_key = True)
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    studentno = db.Column(db.Integer)
    email = db.Column(db.String(120), unique=True)
    pwdhash = db.Column(db.String(54))
    email_confirmation_sent_on = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, nullable=True, default=False)
    email_confirmed_on = db.Column(db.DateTime, nullable=True)

    def __init__(self, firstname, lastname, studentno, email, password, email_confirmation_sent_on=None):
        self.firstname = firstname.title()
        self.lastname = lastname.title()
        self.studentno = studentno.title()
        self.email = email.lower()
        self.set_password(password)
        self.email_confirmation_sent_on = email_confirmation_sent_on
        self.email_confirmed = False
        self.email_confirmed_on = None

    def set_password(self, password):
        self.pwdhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.pwdhash, password)



class SubmissionPracticeQuiz(db.Model):

    __tablename__ = "practice"

    submissionid = db.Column(db.Integer, primary_key=True)
    studentno = db.Column(db.Integer)
    submissiontime = db.Column(db.DateTime(timezone=True))
    correct = db.Column(db.Boolean)
    incomplete = db.Column(db.Boolean)

    q1 = db.Column(db.String())
    q2 = db.Column(db.String())
    q3 = db.Column(db.String())
    q4_image = db.Column(db.String())

    def __init__(self, studentno, submissiontime, correct, incomplete, q1, q2, q3, q4_image):
        self.studentno = studentno
        self.submissiontime = submissiontime
        self.correct = correct
        self.incomplete = incomplete
        self.q1 = q1
        self.q2 = q2
        self.q3 = q3
        self.q4_image = q4_image


