# Signup App (Flask)

A simple application which allowing users to sign up for a project team. 

## Projects

Any user can create a project which any other use can join. 

## Auth

This application uses GitHub Authentication. 

To create a GitHub OAuth application follow instructions [here](https://docs.github.com/en/free-pro-team@latest/developers/apps/creating-an-oauth-app).

Once created set your environment variables as:
```bash
export GITHUB_CLIENT_ID=<your client id>
export GITHUB_SECRET_KEY=<your secret key>
```

## Database

This application is set up to use MongoDB. We have used Mongo Cloud (available at [cloud.mongodb.com](https://cloud.mongodb.com/)), but you can replace this with any local or otherwise hosted MongoDB instance as you see fit. 

Wherever you choose to host your Mongo, you will need to have the following environment variable for your app to work.

```bash
export MONGODB_URI=<your mongo uri>
```
