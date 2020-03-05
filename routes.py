from typing import Any
from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_uploads import UploadSet, configure_uploads, IMAGES, SCRIPTS, patch_request_class, UploadNotAllowed
from flask_basicauth import BasicAuth
from models import db, User
from forms import SignupForm, LoginForm, QueryForm, SubmissionForm, PracticeQuiz, EmailForm, PasswordForm, MarkingForm
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy import desc
from os.path import join
import datetime
from due_dates import *
import os
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from response import Response, images, scripts
from exceptions import CodeFailException, ImageFailException
import importlib

application = Flask(__name__, static_url_path="")

application.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///coderquiz2019'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
application.config['UPLOADED_IMAGES_DEST'] = os.getcwd() + "/static/uploads"
application.config['UPLOADED_SCRIPTS_DEST'] = os.getcwd() + "/static/scripts"

configure_uploads(application, images)
configure_uploads(application, scripts)

application.config['BASIC_AUTH_USERNAME'] = 'john'
application.config['BASIC_AUTH_PASSWORD'] = 'matrix22'

patch_request_class(application)

basic_auth = BasicAuth(application)


db.init_app(application)

application.secret_key = 'set_this_key_outside_if_deployed'

BASE_ROUTE = '/coderquiz'

models_module = importlib.import_module('models')
forms_module = importlib.import_module('forms')

def local(route: str) -> str:
    if BASE_ROUTE == '/':
        return route
    else:
        return join(BASE_ROUTE, route[1:])


def local_url_for(*args, **kwargs) -> str:
    new_url = local(url_for(*args, **kwargs))
    if new_url.count(BASE_ROUTE[1:]) == 1:
        return new_url
    else:
        fixed_url = '/'.join(new_url.split('/')[2:])
    assert fixed_url.count(BASE_ROUTE[1:]) == 1, fixed_url
    return fixed_url


def url_for_static(filename):
    root = application.config.get('STATIC_ROOT', '')

def local_redirect(*args, **kwargs) -> Any:
    return redirect(local_url_for(*args, **kwargs))

def manual_validation(form):
    """
    Validation that only checks that non-image and non-code fields are valid, as image and code fields need to be
    checked separately
    :param form: The form to check
    :return: Boolean representing if the non-image and non-code fields are valid
    """
    valid = True
    for question in form:
        if "_image" not in question.id and "_code" not in question.id:
            if not question.validate(form):
                return False
    return valid


def create_page(form, form_url):
    questions = form.questions
    uploaded = [] # To keep track of which files have been uploaded to the server

    if request.method == "POST":
        print ('sesssion is ', session)
        try:
            if form.check.data:

               # User is checking their responses
                form.validate()
                for item in form.data.keys():
                    if "_code" in item:
                        if form.data[item]:
                            if "." not in form.data[item].filename or form.data[item].filename.split(".")[1] != 'py':

                                form.data.pop(item)
                                form.validate()
                                raise CodeFailException("Your code should be a Python file ending in .py")
                            filename = scripts.save(form.data[item], name=str(session['studentno'])  + "_" + item + ".")

                            session[ form.form_name + "_" + item] = os.getcwd() + "/static/scripts/" + filename

                    if "_image" in item:
                        if form.data[item]:
                            try:
                                filename = images.save(form.data[item], name=str(session['studentno'])  + "_" + item
                                                                             + "." )

                            except UploadNotAllowed:
                                form.data[item] = None
                                form.validate()
                                raise ImageFailException("Your image upload is not an accepted image file")

                            session[form.form_name + "_" + item] = os.getcwd() + "/static/uploads/" + filename

                return render_template(form_url, questions=questions, form=form, uploaded=uploaded)


            elif form.submit.data: # User is submitting their responses

                responses = Response(form, form_url)

                # Create a list for holding the images and code submissions that appear incorrect but are stored in
                # session
                session_correct = []

                answers = responses.get_result()
                class_ = getattr(models_module, form.submission_form)

                # Need to check if code submission is empty, and if it is - if it exists in the session variable (i.e.
                # it existed at some point and then the user hit check

                for idx, question in enumerate(questions):
                    if "_code" in question and len(answers[idx]) > 2 and answers[idx] != "INCOMPLETE":
                        answers[idx] = open(os.getcwd() + "/static/scripts/" + answers[idx].split("/")[-1],
                                                 'rb').read()
                        session_correct.append(question)

                for idx, question in enumerate(questions):
                    print (answers)
                    if "_code" in question and not answers[idx] and form.form_name + "_" + question in session:
                            answers[idx] = open(session[form.form_name + "_" + question], 'rb').read()
                            session_correct.append(question)

                    if "_image" in question and len(answers[idx]) > 2:

                            answers[idx] = os.getcwd() + "/static/uploads/" + answers[idx].split("/")[-1]
                            session_correct.append(question)

                # Check if there are any errors in validating the form, and also check if these are errors due to code
                # or images not appearing when the code or images have been stored in the session
                correct = True
                form.validate()

                for err in form.errors.keys():
                    if err not in session_correct:
                        correct = False
                        break

                if "InClass" in form.form_name and not correct:
                    error_msg = "Your answers must either be validated as correct or completely blank. You must " \
                                "submit a .py file (submit a blank .py file if necessary)"
                    return render_template(form_url, questions=questions, form=form, uploaded=uploaded,error=error_msg )

                else:

                    incomplete = False

                    # Check if it was incomplete
                    for answer in answers:
                        if answer == "INCOMPLETE" or answer == b'' or answer == '':
                            incomplete = True
                        if "InClass" in form.form_name and incomplete:
                            correct = False

                    form_submission = class_('12345678', responses.dt, correct, incomplete, *answers)

                    for item in session:
                        if "_code" in item:
                            pass

                    db.session.add(form_submission)
                    db.session.commit()

                    # Clear out all the records of submitted code and delete the temporarily uploaded code
                    [session.pop(key) for key in list(session.keys()) if key != 'studentno' and key != 'csrf_token']

                    return render_template('success.html', form=form, url_for=url_for, correct=correct,
                                           incomplete=incomplete)

        except (CodeFailException, ImageFailException) as e:
            return render_template(form_url, questions=questions, form=form, uploaded=uploaded,
                                   error=e)

    elif request.method == "GET":
        return render_template(form_url, questions=questions, form=form, uploaded=uploaded)


@application.route(local("/"))
def index():
        return render_template('landing.html', url_for=url_for)





@application.route(local("/landing"))
def landing():
    return render_template("landing.html", studentno=session['studentno'],
                               url_for=url_for)

@application.route(local("/practice"), methods=["GET", "POST"])
def practice():
    form = PracticeQuiz()
    return create_page(form, 'practice.html')


@application.route(local("/submissiondynamic"), methods=["GET", "POST"])
def submissiondynamic():
    form = SubmissionForm()
    if request.method == "POST":
        studentno = '12345678'  # Student number
        item = form.assessment_item.data  # Submission form data

        form_name = item[10:]

        submission_form = getattr(models_module, item)

        if form.records.data == 'Latest':
            results = [submission_form.query.filter_by(studentno=studentno).order_by(desc("submissiontime")).limit(1).first()]

            if results[0] == None:
                return render_template("submissiondynamic.html", form=form,
                                       errors="You haven't submitted this assessment item")

            edited_results = build_results(results, form_name)

            return render_template("submissiondynamic.html", form=form, studentno=studentno, results=edited_results)

        elif form.records.data == 'All':
            results = submission_form.query.filter_by(studentno=studentno).order_by(desc("submissiontime"))

            if not results.count():
                return render_template("submissiondynamic.html", form=form,
                                       errors="You haven't submitted this assessment item")

            edited_results = build_results(results, form_name)

            return render_template("submissiondynamic.html", form=form, studentno=studentno, results=edited_results)


        else:
            return render_template("submissiondynamic.html", form=form)



    else:
        return render_template("submissiondynamic.html", form=form)




def build_results(results, form_name):
    """
    Take a list of submissions and return an edited list of dictionaries that seperates the different information
    :param results: The list of submissions
    :return: A list of dictionaries with the edited results
    """
    edited_results = []

    form = getattr(forms_module, form_name)
    questions = form.questions
    due_date = (duedates[form_name])
    for result in results:
        correct = result.correct
        incomplete = result.incomplete
        late = result.submissiontime > due_date
        submission_time = str(result.submissiontime).split(".")[0]
        joined_list = []
        code_list = []
        image_list = []
        for question in questions:
            answer = getattr(result, question)
            if 'image' in question:
                filepath = "/uploads/" + answer.split("/")[-1]
                image_list.append([question, filepath])
            elif type(answer) == str:
                joined_list.append([question, answer])
            elif 'code' in question:
                code_list.append([question, highlight(answer, PythonLexer(), HtmlFormatter())])
        edited_result = {"results": joined_list, "late": late, "submission_time": submission_time, "correct": correct,
                         "incomplete": incomplete, "code_list": code_list,
                         "image_list": image_list}
        edited_results.append(edited_result)

    return edited_results


@application.route(local("/query"), methods=["GET", "POST"])
def query():
    if 'studentno' not in session:
        return redirect(url_for('login'))

    form = QueryForm()

    if request.method == "POST" and not form.studentno.data:
        return render_template("query.html", form=form)

    elif request.method == "POST" and form.submit.data:
        studentno = form.studentno.data
        item = form.assessment_item.data
        form_name = item[10:]
        inclass = True if "InClass" in form_name else False

        submission_form = getattr(models_module, item)


        if form.records.data == 'Latest':
            results = [submission_form.query.filter_by(studentno=studentno).order_by(desc("submissiontime")).limit(1).first()]
            if (results[0] == None):
                return render_template("query.html", form=form,
                                       errors="This student hasn't submitted this assessment item")

            edited_results = build_results(results, form_name)

            return render_template("query.html", form=form, studentno=studentno, results=edited_results)

        elif form.records.data == 'All':
            results = submission_form.query.filter_by(studentno=studentno).order_by(desc("submissiontime"))

            if not results.count():
                return render_template("query.html", form=form,
                                       errors="This student hasn't submitted this assessment item")

            edited_results = build_results(results, form_name)

            return render_template("query.html", form=form, studentno=studentno, results=edited_results)


        else:
            return render_template("query.html", form=form)

    ### BELOW WAS FOR DOWNLOADING FILES

    # elif request.method == "POST" and form.download.data:
    #     studentno = form.studentno.data
    #     file_data = Submission.query.filter_by(studentno=studentno).order_by(desc('submissiontime')).limit(1).first()
    #     return send_file(BytesIO(file_data.file_upload), attachment_filename=studentno + "_Q2.py", as_attachment=True)
    #
    #
    # elif request.method == "POST" and form.download2.data:
    #     studentno = form.studentno.data
    #     file_data = Submission.query.filter_by(studentno=studentno).order_by(desc('submissiontime')).limit(1).first()
    #     return send_file(BytesIO(file_data.file_upload), attachment_filename=studentno + "_Q3.py", as_attachment=True)


    if 'studentno' not in session:
        return redirect(url_for('login'))
    else:
        return render_template("query.html", form=form)


@application.route(local("/marking"), methods=["GET", "POST"])
def marking():
    if 'studentno' not in session:
        return redirect(url_for('login'))

    form = MarkingForm()

    if request.method == "POST" and form.submit.data:
        item = form.assessment_item.data
        form_name = item[10:]
        submission_form = getattr(models_module, item)

        generated_results = {"Correct": [], "Complete": [], "Incomplete": [], "Missing": [], "Late": []}

        students = User.query.order_by(User.studentno).all()

        for student in students:

            # Check to see if the student submitted anything
            exists = db.session.query(submission_form).filter_by(studentno=student.studentno).first() is not None
            if exists:
                correct = complete = incomplete = late = False
                due_date = (duedates[form_name])

                results = submission_form.query.filter_by(studentno=student.studentno).order_by("submissiontime")
                if (results[0] != None):
                    for result in results:
                        if result.submissiontime < due_date:
                            if result.correct:
                                correct = True
                                break
                            elif not result.incomplete:
                                complete = True
                            elif result.incomplete:
                                incomplete = True

                        elif result.submissiontime >= due_date:
                            late = True

                if correct:
                    generated_results["Correct"].append([student.studentno, student.firstname, student.lastname])
                elif complete:
                    generated_results["Complete"].append([student.studentno, student.firstname, student.lastname])
                elif incomplete:
                    generated_results["Incomplete"].append([student.studentno, student.firstname, student.lastname])
                elif late:
                    generated_results["Late"].append([student.studentno, student.firstname, student.lastname])

            else:
                generated_results["Missing"].append([student.studentno, student.firstname, student.lastname])

        return render_template("marking.html", form=form, item=item, generated_results=generated_results)

    if 'studentno' not in session:
        return redirect(url_for('login'))
    else:
        return render_template("marking.html", form=form)

@application.route(local('/marking/<item>/<token>'), methods=["GET", "POST"])
def marking_with_token(token, item):
    studentno = token
    form_name = item[10:]
    inclass = True if "Assessment" in form_name else False

    submission_form = getattr(models_module, item)

    results = submission_form.query.filter_by(studentno=studentno).order_by(desc("submissiontime"))

    if not results.count():
        return render_template("marking_result.html",
                               errors="This student hasn't submitted this assessment item")

    edited_results = build_results(results, form_name)

    return render_template("marking_result.html", studentno=studentno, results=edited_results)

if __name__ == "__main__":
    application.run(debug=True)
    session['studentno'] = 12345678
    form = PracticeQuiz()
