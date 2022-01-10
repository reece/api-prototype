# API Prototype

This directory contains a sketch of how to implement an API-first
design using OpenAPI 3.0, Connexion/Flask, and JWT, primarily as a
proof-of-concept for machine-to-machine (B2B) integration.

## Intended flow

* Partner authenticates at Auth0 using a client secret to obtain a
  JWT. The JWT is signed using a private key. The Partner presents the
  JWT to this API for all requests, which validates the JWT using the
  public key.  The intended architectural pattern is to centralize
  authn/z services away from the API itself.

* When the API receives a request, it is validated and queued, and a
  request id is returned to the client. In the real world, this
  request would be queued in AWS SQS, ZeroMQ, Redis, or similar
  high-availability service.
  
* A client later request status using the request_id.


![Sequence Diagram](docs/sequence.png)


## Features

* API designed first using OpenAPI 3
* Python, using Connexion
* JSON Web Token (JWT) for authentication and authorization


## Installing

- auth0 setup
- config.yaml


    $ python3 -m venv venv
    $ source venv/bin/activate
    $ pip install -U setuptools pip
    $ pip install -r requirements.txt
    $ python3 app.py

Or in production, more like:

    $ gunicorn --access-logfile=-  app:app



Then go to http://localhost:8080/ui/ 
