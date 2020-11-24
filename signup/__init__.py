import os

from flask import (
    Flask, jsonify, session, g, redirect, url_for,
    render_template, request
)
from flask_pymongo import PyMongo
from flask_github import GitHub


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        MONGO_URI=os.environ.get('MONGO_URI', 'localhost:27017'),
        GITHUB_CLIENT_ID=os.environ.get('GITHUB_CLIENT_ID'),
        GITHUB_CLIENT_SECRET=os.environ.get("GITHUB_SECRET_KEY")
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Making a Mongo Connection to our database
    mongo = PyMongo(app)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return jsonify({"title": 'Hello, World!'})

    github = GitHub(app)

    @app.before_request
    def before_request():
        g.user = None
        if 'user_id' in session:
            g.user = mongo.db.user.find({'_id': session['user_id']})
        
    @app.route('/')
    def index():
        uid = session.get('user_id', None)
        users = None
        if uid is not None:
            users = mongo.db.user.find({'_id': session.get('user_id')})
        projects = mongo.db.project.find()

        return render_template('home.html', user=users, projects=projects)
    
    
    @app.route('/github-callback')
    @github.authorized_handler
    def authorized(access_token):
        next_url = request.args.get('next') or url_for('index')
        if access_token is None:
            return redirect(next_url)

        user = mongo.db.user.find_one({'github_access_token': access_token})
        if user is None:
            github_user = github.get('/user')
            user = {
                'github_access_token': access_token,
                '_id': github_user['login'],
                'email': github_user['email'],
                'github_profile': github_user['html_url'],
                'name': github_user['name'] 
            }
            mongo.db.user.insert_one(user)
        
        g.user = user

        session['user_id'] = user['_id']
        return redirect(next_url)
    
    @app.route('/login')
    def login():
        if session.get('user_id', None) is None:
            return github.authorize()
        else:
            return redirect(url_for('index'))
    
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('index'))

    
    return app