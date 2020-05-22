import os
from datetime import datetime
import requests

from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# we definde the goodreads api API_KEY and URL
API_KEY = {goodreads_api_key}
GOODREADS_URL = 'https://www.goodreads.com/book/review_counts.json'

def session_login(username):
    ''' Save session variables to use when the user is logged in '''
    session['LOGGED'] = True
    session['USER_ID'] = db.execute("SELECT id FROM users WHERE username = :username", {'username':username}).fetchone()
    session['USERNAME'] = username

def session_logout():
    ''' Erase session variables when user logs out '''
    session['LOGGED'] = False
    session['USER_ID'] = None
    session['USERNAME'] = None

@app.route("/")
def index():
    # check if the user has been logged in
    if session.get('LOGGED') is None:
        session['LOGGED'] = False

    return render_template('index.html')



@app.route('/login')
def login_page():
    return render_template('login_logout.html')

@app.route('/login/<string:type>', methods=['POST'])
def login(type):
    ''' Type equals login or register '''
    username = request.form.get('username')
    password = request.form.get('password')

    username_true = db.execute('SELECT username FROM users WHERE username = :username', {'username':username})
    # If user tries to login
    if type == 'login':
        # check if user exists
        if username_true.rowcount == 0:
            return render_template('login_logout.html', error='login', message='Invalid Username or Password!')

        # If user exists, check if password is correct
        password_real = db.execute('SELECT password FROM users WHERE username = :username', {'username':username}).fetchone()
        if password != password_real[0]:
            return render_template('login_logout.html', error='login', message='Invalid Username or Password!')

    # If user tries to register
    if type == 'register':

        # Check if username already exists
        if username_true.rowcount != 0:
            return render_template('login_logout.html', error='register', message='Username already exists!')

        repeat_password = request.form.get('repeat_password')
        if repeat_password != password:
            return render_template('login_logout.html', error='register', message='Passwords do not match!')



        # Register user in database
        db.execute('INSERT INTO users (username, password) VALUES (:username, :password)',
                    {'username':username, 'password':password})

        db.commit()


    session_login(username)
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session_logout()
    return redirect( url_for('login_page') )


@app.route('/book_search')
def book_search():
    ''' Page to search for a book '''
    # Check if user has logged in
    if session['LOGGED'] == False:
        return redirect(url_for('index'))

    return render_template('book_search.html')


@app.route('/book_list', methods=['POST'])
def book_list():
    query = request.form.get('search')
    search = "%{}%".format(query)
    # Select books that match the query
    books = db.execute("SELECT * FROM books WHERE isbn LIKE :search OR title LIKE :search OR author LIKE :search",
                        {'search':search})



    return render_template('book_list.html', books=books)


@app.route('/book_search/<int:book_id>')
def book_page(book_id):
    book = db.execute("SELECT * FROM books WHERE id = :book_id", {'book_id':book_id}).fetchone()
    reviews = db.execute("SELECT * from reviews WHERE book_id = :book_id ORDER BY timestamp DESC", {'book_id':book_id}).fetchall()


    # Obtain data from good reads API
    res = requests.get(GOODREADS_URL, params={'key':API_KEY, 'isbns':book.isbn})
    api_data = res.json()

    return render_template('book_page.html', book=book, reviews=reviews, api_data=api_data)

@app.route('/leave_review/<int:book_id>', methods=['POST'])
def leave_review(book_id):
    ''' Method to leave a review for a book '''
    username = session['USERNAME']
    user_id = session['USER_ID'][0]
    review = request.form.get('review')
    rating = request.form.get('rating')
    dt = datetime.now()

    # Check if review exists
    if db.execute("SELECT * FROM reviews WHERE user_id=:user_id AND book_id=:book_id",{'user_id':user_id, 'book_id':book_id}).rowcount != 0:
        return render_template('message.html', message='Already left a review for this book.')

    db.execute("INSERT INTO reviews (username, user_id, book_id, review, rating, timestamp) VALUES (:username, :user_id, :book_id, :review, :rating, :timestamp)",
                {'username':username, 'user_id':user_id, 'book_id':book_id, 'review':review, 'rating':rating, 'timestamp':dt})
    db.commit()

    return redirect( url_for('book_page', book_id=book_id))

@app.route('/api/<string:isbn>')
def book_api(isbn):
    ''' Return the details about a specific book '''

    # Make sure book exists
    book = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn':isbn}).fetchone()
    if book is None:
        return jsonify({'error': 'Invalid ISBN'}), 422

    reviews = db.execute("SELECT COUNT(*), AVG(rating) FROM reviews WHERE book_id = :book_id", {'book_id': book.id}).fetchone()
    print(reviews[0])

    return jsonify({'title': book['title'],
                    'author': book.author,
                    'year': book.year,
                    'isbn': book.isbn,
                    'review_count': reviews[0],
                    'average_score': str(reviews[1])
                    })
