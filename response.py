from datetime import datetime
import pytz
from flask import request
from exceptions import CodeFailException, ImageFailException
from werkzeug.datastructures import FileStorage
from flask import session
from flask_uploads import UploadSet, configure_uploads, IMAGES, SCRIPTS, UploadNotAllowed


images = UploadSet('images', IMAGES)
scripts = UploadSet('scripts', SCRIPTS)

class Response:
    """
    A class for holding a user's response to a quiz
    """
    responses = []
    incomplete = False

    def __init__(self, form, form_url):

        self.questions = form.questions
        self.form = form
        self.form_url = form_url
        self.dt = datetime.now(pytz.timezone('Australia/Brisbane'))
        self.incomplete = False

    def get_result(self):
        self.responses = []

        for question in self.questions:

            # Handle questions that asked for code differently
            if "_code" in question:
                print ('got to here')
                question_name = getattr(self.form, question).name

                if str(question_name) in request.files:
                    print (question_name + " was in request files")
                    code = request.files[str(question_name)]

                    if code:

                        if "." not in code.filename or code.filename.split(".")[1] != 'py':
                            session[question_name] = "Format Error"

                            raise CodeFailException("Your code upload should be a Python file ending in .py")
                        else:
                            filename = scripts.save(code, name=str(session['studentno']) + "_" + question_name +
                                                                   ".")
                            url = scripts.url(filename)
                            self.responses.append(url)

                    else:  # Code wasn't in the current submission, but it might be stored in the session data
                        if session.get(question_name) is not None:
                            url = session[question_name]
                            self.responses.append(open(url, 'rb').read())

                        else:  # Code wasn't in the current submission or the saved session data
                            code = FileStorage()
                            self.incomplete = True
                            self.responses.append(code.read())

            # Handle questions that asked for images differently
            elif "_image" in question:

                question_name = getattr(self.form, question).name

                if getattr(self.form, question).data:
                    try:
                        filename = images.save(getattr(self.form, question).data, name=str(session['studentno']) + "_" +
                                                                                       question_name +
                                                                                       ".")
                        url = images.url(filename)
                        self.responses.append(url)

                    except UploadNotAllowed:

                        session[question_name] = "Format Error"

                        raise ImageFailException("Your image upload is not an accepted image file")

                else:  # Image wasn't in the current submission, but it might be in the session data

                    if session.get(self.form.form_name + "_" + question_name) is not None:
                        url = session[self.form.form_name + "_" + question_name]
                        self.responses.append(url)

                    else:  # Code wasn't in the current submission or the saved submission data
                        url = ""
                        self.incomplete = True
                        self.responses.append(url)

            # Handle all the questions that just want text
            else:
                response = getattr(self.form, question).data

                if response:
                    result = response
                else:
                    result = "INCOMPLETE"
                    self.incomplete = True

                self.responses.append(result)

        return self.responses
