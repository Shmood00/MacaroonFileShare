from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, MultipleFileField, SelectField
from wtforms.validators import InputRequired, Email, Length

#Create login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8,max=80)])

#Create register form
class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])

#Create file upload form
class FileUpload(FlaskForm):
    image = MultipleFileField('image', validators=[InputRequired()])

#Create share image form
class MakeToken(FlaskForm):
    user_email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
  
    image_name = SelectField('Image Name', validators=[InputRequired()])

    expiry_time = SelectField('Expiry Time', validators=[InputRequired()])

#Create verify macaroon form
class VerifyEmail(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
