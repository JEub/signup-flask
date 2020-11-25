import os

from flask import (
    Flask, jsonify, session, g, redirect, url_for,
    render_template, request, abort
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
            g.user = mongo.db.user.find_one({'user_id': session['user_id']})
        
    @app.route('/')
    def index():
        uid = session.get('user_id', None)
        users = None
        if uid is not None:
            users = mongo.db.user.find_one({'user_id': session.get('user_id')})
            print(users)
        projects = mongo.db.project.find()

        return render_template('home.html', user=users, projects=projects)
    
    @github.access_token_getter
    def token_getter():
        user = g.user
        if user is not None:
            return user.get('github_access_token', None)
    
    @app.route('/github-callback')
    @github.authorized_handler
    def authorized(access_token):
        next_url = request.args.get('next') or url_for('index')
        if access_token is None:
            return redirect(next_url)

        user = mongo.db.user.find_one({'github_access_token': access_token})
        if user is None:
            
            user = {
                'github_access_token': access_token
            }
        
        user['github_access_token'] = access_token

        g.user = user

        if user.get('user_id', None) is None:
            github_user = github.get('/user')

            user['user_id'] = github_user['login']
            user['email'] = github_user['email']
            user['profile'] = github_user['html_url']
            user['name'] = github_user['name']

            mongo.db.user.replace_one({"user_id": user['user_id']}, user, upsert=True)

        g.user = user
        session['user_id'] = user['user_id']
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

    @app.route('/projects/all')
    def projects():
        projects = [proj for proj in mongo.db.projects.find()]
        return jsonify(projects)

    @app.route('/projects/<name:str>')
    def get_project(name):
        project = mongo.db.projects.find_one({'project_name': name})
        return jsonify(project)

    @app.route('/projects/create', method=['POST'])
    def create_project():
        if session.get('user_id', None) is None:
            return abort(401, 'Log in to post a new project.')
        
        body = request.get_json()
        # TODO validate project data exists in form request

        # TODO verify project name is unique or redirect

        # TODO return and redirect to posted project details

    @app.route('/projects/<name:str>/update', method=['POST'])
    def update_project(name):
        if session.get('user_id', None) is None:
            return abort(401, 'Log in to update a project.')
        
        project = mongo.db.projects.find_one({'project_name', name})

        if project is None:
            return abort(400, 'Project not found.')
        elif project['owner_id'] != session['user_id']:
            return abort(401, 'You are not the project owner.')
        
        body = request.get_json()

        for key in body:
            if (key in project.keys()) and (key not in ['project_name',]):
                project[key] = body[key]
        
        mongo.db.projects.replace_one(
            {'project_name': project['project_name']},
            project, upsert=True
            )
        
        return jsonify(project), 200

    return app