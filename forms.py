from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, MultipleFileField, SelectField
from wtforms.validators import InputRequired, Email, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8,max=80)])
    remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])

class FileUpload(FlaskForm):
    image = MultipleFileField('image', validators=[InputRequired()])

class MakeToken(FlaskForm):
    user_email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
  
    image_name = SelectField('Image Name', validators=[InputRequired()])


class VerifyEmail(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])