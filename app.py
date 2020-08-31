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

app = Flask(__name__)
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////{}/Projects//MacaroonFileShare/login.db'.format(os.path.expanduser('~'))
app.config['UPLOADED_IMAGES_DEST'] = 'uploads/images'

images = UploadSet('images', IMAGES)
configure_uploads(app, images)

def get_images():
    names = [os.path.basename(x) for x in glob.glob('{}/*'.format(app.config['UPLOADED_IMAGES_DEST']))]

    return names

keys = {
    'secret-key': app.config['SECRET_KEY']
}


@login_manager.user_loader
def load_user(user_id):
    return models.User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    return render_template('index.html', user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()

    if form.validate_on_submit():
        user = models.User.query.filter_by(username=form.username.data).first()

        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('index'))
        else:
        
            flash("Invalid Credentials")

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = forms.RegisterForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = models.User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Created new user!")


    return render_template('register.html', form=form)

@app.route('/protected', methods=['GET', 'POST'])
@login_required
def protected():

    form = forms.FileUpload()
    file_count = 0
    if form.validate_on_submit():

        
        for file in form.image.data:
            
            filename = secure_filename(file.filename)
            
            if os.path.isdir(app.config['UPLOADED_IMAGES_DEST']):
                file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                file_count += 1
            else:
                
                os.makedirs(app.config['UPLOADED_IMAGES_DEST'])
                file.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                file_count += 1    

        flash("Uploaded {} image(s)".format(file_count))

    return render_template('secret.html', form=form)


@app.route('/make_token', methods=['GET', 'POST'])
@login_required
def make_token():

    form = forms.MakeToken()

    names = get_images()

    names.insert(0, "Select Image")

    form.image_name.choices = [(name, name) for name in names]

    if form.validate_on_submit():
        email = form.user_email.data

        ###Create macaroon so entered email can view image
        m = Macaroon(
            location='http://localhost:5000/gallery/{}'.format(form.image_name.data),
            identifier='secret-key',
            key=keys['secret-key']
        )

        m.add_first_party_caveat('email = {}'.format(email))
        m.add_first_party_caveat('image_name = {}'.format(form.image_name.data))

        ###ONLY FOR VM
        try:
            vm_ip = ni.ifaddresses('ens33')[ni.AF_INET][0]['addr']
        except:
            try:
                vm_ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
            except:
                vm_ip = ni.ifaddresses('wlan0')[ni.AF_INET][0]['addr']

      
        final_link = "http://{}:5000/gallery/{}/{}".format(vm_ip, m.serialize(), form.image_name.data)

        flash(Markup("Give this user the following link:<br /><a href={}>{}</a>".format(final_link, final_link)))


    return render_template('make_token.html', form=form, images=names)

@app.route('/gallery')
@login_required
def all_images():
    images = get_images()

    return render_template('gallery.html', images=images)

@app.route('/gallery/<image_name>')
@login_required
def gallery(image_name):

    try:
        return send_from_directory(app.config['UPLOADED_IMAGES_DEST'], filename=image_name, as_attachment=False)
    except:
        return render_template('gallery.html')

#WITH TOKEN
@app.route('/gallery/<token>/<image_name>', methods=['GET', 'POST'])
def gallery_token(token, image_name):

    if token:

        ##Decode token
        n = Macaroon.deserialize(token)
        v = Verifier()

        form = forms.VerifyEmail()

        if form.validate_on_submit():
            v.satisfy_exact('email = {}'.format(form.email.data))
            v.satisfy_exact('image_name = {}'.format(image_name))

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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

