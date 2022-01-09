# MyOme API Prototype

This directory contains an example of how to implement an API-first
design using OpenAPI 3.0, Connexion + Flask, and JWT.

This code assumes that the JWT will be generated at Auth0.  See
Auth0.ipynb for details.


## Getting started

    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install -U setuptools pip
    $ pip install -r requirements.txt
    $ python3 app.py


Or in production, more like:

    $ gunicorn --access-logfile=-  app:app



Then go to http://localhost:8080/ui/ 
