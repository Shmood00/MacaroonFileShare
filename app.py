from flask import Flask, render_template, flash, redirect, url_for, send_from_directory, Markup
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymacaroons import Macaroon, Verifier
from flask_uploads import configure_uploads, IMAGES, UploadSet
from werkzeug.utils import secure_filename
import glob, os
import netifaces as ni
import models
import forms
from datetime import datetime, timedelta

app = Flask(__name__)
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

current_dir = os.getcwd()

#Flask app configurations
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////{}/login.db'.format(current_dir)
app.config['UPLOADED_IMAGES_DEST'] = 'uploads/images'

images = UploadSet('images', IMAGES)
configure_uploads(app, images)

#Function to retreive names of all images in uploads/images folder
def get_images():
    names = [os.path.basename(x) for x in glob.glob('{}/*'.format(app.config['UPLOADED_IMAGES_DEST']))]

    return names

#Function that checks Macaroon 
def check_expiry(caveat):
    if not caveat.startswith('time < '):
        return False
    
    try:
        now = datetime.now()
        when = datetime.strptime(caveat[7:], '%Y-%m-%d %H:%M:%S.%f')

        return now < when
    except:
        return False


keys = {
    'secret-key': app.config['SECRET_KEY']
}


@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))

#Defining the index route
@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

#Defining the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()

    #On valid for submission
    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()

        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('index'))
        else:
        
            flash("Invalid Credentials")

    return render_template('login.html', form=form)

#Defining register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegisterForm()
    
    #On valid for submission
    if form.validate_on_submit():
        
        #Compare hashed password
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        
        #Create new user in db
        new_user = models.User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Created new user!")


    return render_template('register.html', form=form)

#Defining file upload route
@app.route('/protected', methods=['GET', 'POST'])
@login_required
def protected():

    form = forms.FileUpload()
    file_count = 0
    
    #On valid for submission
    if form.validate_on_submit():

        #Save each image uploaded to uploads/images folder
        for file in form.image.data:
            
            filename = secure_filename(file.filename)
            
            #Check if uploads/images folders exist
            if os.path.isdir(app.config['UPLOADED_IMAGES_DEST']):
                file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                file_count += 1
            else:
                
                os.makedirs(app.config['UPLOADED_IMAGES_DEST'])
                file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                file_count += 1    

        flash("Uploaded {} image(s)".format(file_count))

    return render_template('secret.html', form=form)

#Create make token route
@app.route('/make_token', methods=['GET', 'POST'])
@login_required
def make_token():

    form = forms.MakeToken()
    
    #Grab image names from uploads/images folder
    names = get_images()

    names.insert(0, "Select Image")

    form.image_name.choices = [(name, name) for name in names]

    form.expiry_time.choices = [(x, '{} minutes'.format(x)) for x in range(1,31)]

    #On valid for submission
    if form.validate_on_submit():
        email = form.user_email.data

        #Create macaroon so entered user email can view image
        m = Macaroon(
            location='http://localhost:5000/gallery/{}'.format(form.image_name.data),
            identifier='secret-key',
            key=keys['secret-key']
        )

        #Get chosen expiry time
        chosen_expiry = int(form.expiry_time.data)

        expiry_time = datetime.now()+timedelta(minutes=chosen_expiry)

        #Add first party caveas to Macaroon
        m.add_first_party_caveat('email = {}'.format(email))
        m.add_first_party_caveat('image_name = {}'.format(form.image_name.data))
        m.add_first_party_caveat('time < {}'.format(expiry_time))

        #Determine IP address for creating access link
        try:
            vm_ip = ni.ifaddresses('ens33')[ni.AF_INET][0]['addr']
        except:
            try:
                vm_ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
            except:
                vm_ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']

      
        #Create share link to be given to user
        final_link = "http://{}:5000/gallery/{}/{}".format(vm_ip, m.serialize(), form.image_name.data)

        flash(Markup("Give this user the following link:<br /><a href={}>{}</a>".format(final_link, final_link)))


    return render_template('make_token.html', form=form, images=names)

#Create gallery route
@app.route('/gallery')
@login_required
def all_images():
    images = get_images()

    return render_template('gallery.html', images=images)

#Create view image route
@app.route('/gallery/<image_name>')
@login_required
def gallery(image_name):

    try:
        return send_from_directory(app.config['UPLOADED_IMAGES_DEST'], filename=image_name, as_attachment=False)
    except:
        return render_template('gallery.html')

#Create shared link validation route
@app.route('/gallery/<token>/<image_name>', methods=['GET', 'POST'])
def gallery_token(token, image_name):

    if token:

        #Decode token
        n = Macaroon.deserialize(token)
        v = Verifier()

        form = forms.VerifyEmail()
        
        #On valid for submission
        if form.validate_on_submit():
            
            #Verify Macaroon is valid
            v.satisfy_exact('email = {}'.format(form.email.data))
            v.satisfy_exact('image_name = {}'.format(image_name))
            v.satisfy_general(check_expiry)

            try:
                verified = v.verify(
                    n,
                    keys[n.identifier]
                )
            
                return send_from_directory(app.config['UPLOADED_IMAGES_DEST'], filename=image_name, as_attachment=False)
            except:
                flash("Unable to access")
                return render_template('validate_email.html', form=form, token=token, image_name=image_name)

        return render_template('validate_email.html', form=form, token=token, image_name=image_name)

    else:
        flash("Unable to access")
        return render_template('validate_email.html', form=form, token=token, image_name=image_name)

#Create logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

