from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from werkzeug.utils import secure_filename
import json
from flask_mail import Mail
import datetime
import os
import math

local_server = True
with open('config.json', 'r') as c:
    params = json.load(c) ['params']
app = Flask(__name__)
app.secret_key = 'website'
app.config ['UPLOAD_FOLDER'] = params ['uploader_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USERNAME=params ['user_gmail'],
    MAIL_PASSWORD=params ['password_gmail'],
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=True,
)
mail = Mail(app)

if local_server:
    app.config ['SQLALCHEMY_DATABASE_URI'] = params ['local_uri']
else:
    app.config ['SQLALCHEMY_DATABASE_URI'] = params ['prod_uri']

db = SQLAlchemy(app)


class Contact(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=False, nullable=False)
    phonenum = db.Column(db.String(15), unique=True, nullable=False)
    message = db.Column(db.String(300), unique=False, nullable=False)


class Codes(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(300), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(15), nullable=True)
    subtitle = db.Column(db.String(30), nullable=True)


per_page = params ['no.of post']


@app.route("/")
def home ():
    # posts = Codes.query.order_by(desc(Codes.date)).limit(params['no.of post']).all()
    posts = Codes.query.order_by(Codes.date.desc())
    page = request.args.get('page')

    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    pages = posts.paginate(page, per_page)

    return render_template('index.html', params=params, posts=posts, pages=pages)


@app.route("/about")
def about ():
    return render_template('about.html', params=params)


@app.route("/contact", methods=['GET', 'POST'])
def contact ():
    if request.method == 'POST':
        '''Add entry to the database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contact(name=name, email=email, phonenum=phone, message=message)
        db.session.add(entry)
        db.session.commit()
        mail.send_message(f'New message from Blog user {name}',
                          sender=email,
                          recipients=[params ['user_gmail']],
                          body=f'{message} \n {phone}'
                          )
    return render_template('contact.html', params=params)


@app.route("/post/<post_slug>", methods=['GET'])
def post (post_slug):
    codes = Codes.query.filter_by(slug=post_slug).first()
    return render_template('post.html', params=params, post=codes)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard ():
    if 'user' in session and session ['user'] == params ['admin_user']:
        posts = Codes.query.all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if username == params ['admin_user'] and userpass == params ['admin_password']:
            session ['user'] = username
            posts = Codes.query.all()
            return render_template('dashboard.html', params=params, posts=posts)
    else:
        return render_template('login.html', params=params)


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit (sno):
    if 'user' in session and session ['user'] == params ['admin_user']:
        if request.method == 'POST':
            title = request.form.get('title')
            sub_title = request.form.get('subtitle')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img = request.form.get('img_file')
            date = datetime.datetime.now()

            if sno == '0':
                post = Codes(title=title, slug=slug, content=content, img_file=img, subtitle=sub_title, date=date)
                db.session.add(post)
                db.session.commit()
            else:
                post = Codes.query.filter_by(sno=sno).first()
                post.title = title
                post.slug = slug
                post.content = content
                post.img_file = img
                post.subtitle = sub_title
                post.date = date
                db.session.commit()
                return redirect(f'/edit/{sno}')
        if sno == '0':
            post = {'sno': '0'}
        else:
            post = Codes.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post)


def allowed_file (filename):
    return '.' in filename and \
           filename.rsplit('.', 1) [1].lower() in params ['allowed_ext']


@app.route("/uploader", methods=['GET', 'POST'])
def uploader ():
    if 'user' in session and session ['user'] == params ['admin_user']:
        if request.method == 'POST':
            f = request.files ['file']
            if f and allowed_file(f.filename):
                f.save(os.path.join(app.config ['UPLOAD_FOLDER'], secure_filename(f.filename)))
                return "Uploaded Successfully."


@app.route("/logout")
def logout ():
    session.pop('user', None)
    return redirect('/dashboard')


@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete (sno):
    if 'user' in session and session ['user'] == params ['admin_user']:
        posts = Codes.query.filter_by(sno=sno).first()
        db.session.delete(posts)
        db.session.commit()
        return redirect('/dashboard')


app.run(debug=True)
