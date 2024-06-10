from flask import Flask, render_template, request, session, url_for, redirect, send_from_directory # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from werkzeug.security import generate_password_hash, check_password_hash
from os import environ 
from datetime import timedelta
import os

UPLOAD_FOLDER = '/app/images'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=1)
app.config['STATIC_FOLDER'] = '/static'
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = environ.get("DB_URL")
db = SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.urandom(24) 

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False) 
    phonenumber = db.Column(db.String(255), nullable=False) 

class Ilan(db.Model):
    __tablename__ = "ilanlar"

    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(255), nullable=False)
    phonenumber = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False) 
    message = db.Column(db.String(255), nullable=False) 
    imagename = db.Column(db.String(255), nullable=False) 

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home_with_slash():
    if "fullname" in session:
        return render_template("home.html", display=True)
    else:
        return render_template("home.html", display=False)

@app.route('/home', methods=['GET'])
def home():
    if "fullname" in session:
        return render_template("home.html", display=True)
    else:
        return render_template("home.html", display=False)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('/app/images', filename) 

@app.route('/kayit-yap', methods=['GET', 'POST'])
def signup_endpoint():
    error = None
    if "fullname" in session:
        return redirect(url_for('home_with_slash'))
    elif request.method == 'POST':
        if is_unique_email(request.form['email']) == False:
            error = "- Bu e-posta adresi zaten kullanımda."
            return render_template("kayit.html", error=error)
        if is_strong_password(request.form['password']) == False:
            error = "- Şifreniz en az 8 karakterden oluşmalı ve en az 3 farklı türde karakter içermelidir."
            return render_template("kayit.html", error=error)
        if is_valid_turkish_phone(request.form['phone']) == False:
            error = "- Geçerli bir telefon numarası giriniz. Örnek: 05XX XXX XX XX"
            return render_template("kayit.html", error=error)
        if is_unique_phone(request.form['phone']) == False:
            error = "- Bu telefon numarası zaten kullanımda."
            return render_template("kayit.html", error=error)
        hashed_password = hash_password(request.form['password'])
        try:
            signup(request.form['fullname'], hashed_password, request.form['email'], request.form['phone'])
            return redirect(url_for('login_endpoint'))
        except Exception:
            error = "Bir hata oluştu. Lütfen tekrar deneyin."
            return render_template("kayit.html", error=error)
    else:
        return render_template("kayit.html")

@app.route('/giris-yap', methods=['GET', 'POST'])
def login_endpoint():
    error = None
    if "fullname" in session:
        return redirect(url_for('home_with_slash'))
    elif request.method == 'POST':  
        try:
            login(request.form['email'], request.form['password'])
            return redirect(url_for('home'))
        except Exception:
            error = "Kullanıcı adı veya şifre hatalı"
            return render_template("giris.html", error=error)
    else:
        return render_template("giris.html")

@app.route('/cikis', methods=['GET'])
def logout_endpoint():
    if "fullname" in session:
        destroy_session()
        return redirect(url_for('home_with_slash'))
    else:  
        return redirect(url_for('home'))

@app.route('/ilan-ekle', methods=['GET','POST'])
def add_ads_endpoint():
    if "fullname" in session:
        if request.method == 'POST':
            add_ads(request.form['konu'], request.form['mesaj'], request.files['resim'], session['fullname'], session['phone'], session['email'])
            info = "İlanınız başarıyla eklendi."
            return render_template("ilan_ekle.html", info=info)
        else:
            return render_template("ilan_ekle.html")
    else: 
        return redirect(url_for('login_endpoint'))

@app.route('/ilanlar', methods=['GET'])
def ads():
    all_ads = Ilan.query.all()
    return render_template("ilanlar.html", ads=all_ads)

def signup(fullname, password, email, phone):
    new_user = User(fullname=fullname, password=password, email=email, phonenumber=phone)
    db.session.add(new_user)
    db.session.commit()

def login(email, password):
    user = User.query.filter_by(email=email).first()
    if user:
        if check_password_hash(user.password, password):
            set_session(user.fullname, user.email, user.phonenumber)
            return True
        else:
            raise Exception
    else:
        raise Exception

def add_ads(title, message, image, author, phonenumber, email):
        ilan = Ilan(title=title, message=message, imagename=image.filename, author=author, phonenumber=phonenumber, email=email)
        db.session.add(ilan)
        db.session.commit()
        path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
        image.save(path)
        return render_template("giris.html", girishata=True)

def set_session(name, email, phone):
    session['fullname'] = name
    session['email'] = email
    session['phone'] = phone
    session.permanent = True

def destroy_session():
    session.pop('fullname', None)
    session.pop('email', None)
    session.pop('phone', None)

def hash_password(password):
    return generate_password_hash(password)

def is_strong_password(password):
    if len(password) < 8:
        return False
    has_lowercase = any(char.islower() for char in password)
    has_uppercase = any(char.isupper() for char in password)
    has_number = any(char.isdigit() for char in password)
    has_symbol = any(not char.isalnum() for char in password)
    if not (has_lowercase + has_uppercase + has_number + has_symbol >= 3):
        return False
    return True

def is_valid_turkish_phone(number):
    cleaned_number = "".join(char for char in number if char.isdigit())
    if len(cleaned_number) != 11:
        return False
    return True
    
def is_unique_email(email):
    user = User.query.filter_by(email=email).first()
    if user:
        return False
    return True

def is_unique_phone(phone):
    user = User.query.filter_by(phonenumber=phone).first()
    if user:
        return False
    return True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int("5000"), debug=True)
