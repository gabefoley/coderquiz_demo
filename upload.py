# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

app = Flask(__name__)
app.config['SECRET_KEY'] = 'I have a dream'
app.config['UPLOADED_IMAGES_DEST'] = os.getcwd() + "/uploads"

images = UploadSet('images', IMAGES)
configure_uploads(app, images)
patch_request_class(app)  # set maximum file size, default is 16MB


class UploadForm(FlaskForm):
    photo = FileField(validators=[FileAllowed(images, u'Image only!'), FileRequired(u'File was empty!')])
    submit = SubmitField(u'Upload')


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        filename = images.save(form.photo.data)
        file_url = images.url(filename)
        print (filename)
        print (file_url)
    else:
        file_url = None
    return render_template('index2.html', form=form, file_url=file_url)


if __name__ == '__main__':
    app.run(port=8091)