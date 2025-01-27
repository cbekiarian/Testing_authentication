from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text,ForeignKey
from typing import List
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkuuBA6O6donzWlSjhBbx7jC0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)
login_manager = LoginManager()
login_manager.init_app(app)
# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User( db.Model, UserMixin):
    __tablename__ = "user"
    id :Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), nullable =False)
    password: Mapped[str] = mapped_column(String(250), nullable =False)
    name: Mapped[str] =mapped_column(String(250),nullable =False)
    posts: Mapped[List["BlogPost"]] = relationship(back_populates="author")
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped["User"] = relationship(back_populates="posts")
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    comments: Mapped[List["Comment"]] = relationship(back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key= True)
    author_id : Mapped[int]= mapped_column(ForeignKey("user.id"))
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped["User"] = relationship(back_populates="comments")
    parent_post: Mapped["BlogPost"] = relationship(back_populates="comments")

# TODO: Create a User table for all your registered users. 

with app.app_context():
    db.create_all()





@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User,user_id)
# TODO: Use Werkzeug to hash the user's password when creating a new user.


def admin_only(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        print(3)
        # if not current_user.is_authenticated :
        #     return abort(403)
        if  current_user.id != 1:
            return abort(403)

        return f(*args,**kwargs)
    return decorated_function

@app.route('/register', methods= ["GET","POST"])
def register():
    form =  RegisterForm()
    if form.validate_on_submit():
        print(form.name)
        print(form.password)
        if db.session.execute(db.select(User).where(User.email == form.email.data)).scalar() != None:

            flash("email already in use, try logging in")
            return redirect(url_for('login'))

        user = User(
            email = form.email.data,
            password= generate_password_hash(password=form.password.data,
                                             method='pbkdf2:sha256',
                                             salt_length=5),
            name = form.name.data
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form = form, current_user = current_user)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods= ["GET","POST"])
def login():
    form = RegisterForm()
    if form.validate_on_submit():

        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user == None:
            flash("Email is not valid")
            return redirect(url_for('login'))
        elif check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Logged in successfully")
            return redirect(url_for('get_all_posts'))
        else:
            flash("wrong password")
            return redirect(url_for('login'))

    return render_template("login.html", form = form, current_user = current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user = current_user)


# TODO: Allow logged-in users to comment on posts

@app.route("/post/<int:post_id>", methods=["GET","POST"])
def show_post(post_id):
    form = CommentForm()

    if form.validate_on_submit():
        if  not current_user.is_authenticated  :
            flash("you need to log in or register to comment")
            return redirect(url_for('login'))
        comment = Comment(
            text = form.comment.data,
            author_id = current_user.id,
            post_id = post_id
        )
        db.session.add(comment)
        db.session.commit()

    comments = db.session.execute(db.select(Comment)).scalars().all()
    requested_post = db.get_or_404(BlogPost, post_id)
    return render_template("post.html", post=requested_post, current_user = current_user, form= form, comments =comments )


# TODO: Use a decorator so only an admin user can create a new post

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,

            date=date.today().strftime("%B %d, %Y"),
            author_id = current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user = current_user)


# TODO: Use a decorator so only an admin user can edit a post

@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user = current_user)


# TODO: Use a decorator so only an admin user can delete a post

@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", current_user = current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user = current_user)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
