import os

from flask import (
    Flask, jsonify, session, g, redirect, url_for,
    render_template, request, abort, flash
)
from flask_pymongo import PyMongo
from flask_github import GitHub

from slugify import slugify

from .projects import project_schema

from .mongoflask import MongoJSONEncoder, ObjectIdConverter


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        MONGO_URI=os.environ.get('MONGO_URI', 'localhost:27017'),
        GITHUB_CLIENT_ID=os.environ.get('GITHUB_CLIENT_ID'),
        GITHUB_CLIENT_SECRET=os.environ.get("GITHUB_SECRET_KEY")
    )
    app.json_encoder = MongoJSONEncoder
    app.url_map.converters['objectid'] = ObjectIdConverter

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

    @app.route('/projects/<slug>')
    def get_project(slug):
        project = mongo.db.projects.find_one({'slug': slug})
        return jsonify(project)

    @app.route('/projects/create', methods=['GET', 'POST'])
    def create_project():

        if request.method == 'GET':
            return render_template('projectForm.html')

        if session.get('user_id', None) is None:
            return abort(401, 'Log in to post a new project.')
        
        body = request.get_json()

        if body.get('project_name', None) is None:
            return abort(400, 'project_name needed in body. None found.')
        
        slug = slugify(body['project_name'])
        if mongo.db.projects.find_one({'slug': slug}) is not None:
            flash(f'Project named {project_name} already exists.')
            return redirect(url_for(get_project, slug=slug))

        project = {
            key: body[key] for key in body.keys()
            if (key != 'comments') and (key in project_schema.keys())
        }

        project['slug'] = slug

        for key in project_schema.keys():
            if key not in project.keys():
                if key in ['comments', 'members']:
                    project[key] = []
                else:
                    project[key] = ""
            
            elif key in ['comments', 'members']:
                if not isinstance(project[key], list):
                    return abort(400, f'Invalid data type passed for {key}. Expected list.')
            elif not isinstance(project[key], str):
                return abort(400, f'Invalid data type passed for {key}. Expected string.')

        mongo.db.projects.replace_one(project, project, upsert=True)
        
        # TODO return and redirect to posted project details
        flash('Project created successfully')
        return redirect(url_for('projects'))

    @app.route('/projects/<slug>/update', methods=['POST'])
    def update_project(slug):
        if session.get('user_id', None) is None:
            return abort(401, 'Log in to update a project.')
        
        project = mongo.db.projects.find_one({'slug', slug})

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

    @app.route('/projects/<slug>/delete')
    def delete_project(slug):
        if session.get('user_id', None) is None:
            return abort(401, 'Log in to delete a project.')

        project = mongo.db.projects.find_one({'slug': slug})

        if project is None:
            return abort(400, 'Project not found.')
        elif project['owner_id'] != session['user_id']:
            return abort(401, 'You are not the project owner.')
        else:
            mongo.db.projects.delete_one({'_id': project['_id']})
        
        return 'Delete successful', 200

    return app