from wtforms.validators import ValidationError
from random import randrange
import sre_constants
import string
from bisect import bisect


class CheckList(object):
    """
    Custom validator for WTForms to check
    if the correct list was submitted
    """

    def __init__(self, correct_list):
        self.correct_list = []
        for item in correct_list.split(","):
            self.correct_list.append(item.upper().strip())

    def __call__(self, form, field):
        if field.data is not None:
            check_list = []
            for item in field.data.split(","):
                check_list.append(item.upper().strip())
            check_set = set(check_list)
            correct_set = set(self.correct_list)

            if len(check_set) > len(correct_set):
                raise ValidationError("You have entered too many responses")

            if len(check_set) < len(correct_set):
                raise ValidationError("You haven't entered enough responses")

            if len(check_set - correct_set) > 0:
                # Get the original formatting of the response
                incorrect_responses = []
                for item in field.data.split(","):
                    if item.upper().strip() in check_set - correct_set:
                        incorrect_responses.append(item.strip())

                raise ValidationError(
                    'The following responses are not correct - {}'.format(', '.join([x for x in incorrect_responses])))


class CorrectAnswer(object):
    """
    Custom validator for WTForms to check
    if the correct answer was submitted
    """

    def __init__(self, answers, list_answer=False):
        self.list_answer = list_answer
        if isinstance(answers, str):
            self.answers = [answers]
        else:
            self.answers = answers

    def __call__(self, form, field):
        # List of error messages that are selected by random
        error_messages = ['Sorry, that\'s not the correct answer.',
                          'Try that again...',
                          'Incorrect answer.',
                          'Please check this answer...',
                          'Oops! Try again...',
                          'Nope! Sorry... try again!',
                          'No, not quite... try again!',
                          'Hmmm, not exactly right...']
        num = randrange(0, len(error_messages))
        message = error_messages[num]

        if field.data is not None:
            # If the answer is a list, not a list of possible answers then check that the list is correct
            if self.list_answer:
                if str(self.answers) == field.data:
                    return
            else:

                for answer in self.answers:
                    if answer.strip().upper() == field.data.strip().upper():
                        return

        raise ValidationError(message)


class CheckPalindrome(object):
    def __call__(self, form, field):
        if field.data is not None:
            cleaned_data = "".join(l for l in field.data.upper() if l not in string.punctuation)
            cleaned_data = cleaned_data.replace(" ", "")

            if cleaned_data == cleaned_data[::-1]:
                return
            else:
                raise ValidationError("That is not a palindrome")




class Unique(object):
    def __init__(self, model, field, message=u'This element already exists.'):
        self.model = model
        self.field = field
        self.message = message

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)


