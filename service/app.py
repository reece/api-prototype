#!/usr/bin/env python3
"""
Partner API demonstration using OpenAPI, JWT, and Connexion+Flask.
"""

import copy
import enum
import hashlib
import json
import logging
import time
import uuid

from werkzeug.exceptions import Unauthorized
import arrow
import connexion
import jwt
import yaml


_logger = logging.getLogger()

config = yaml.load(open("config.yaml"), Loader=yaml.SafeLoader)
jwt_config = config["jwt"]

request_queue = {}


def generate_token():
    timestamp = arrow.utcnow().int_timestamp
    cf = jwt_config["api"]
    payload = {
        "iss": cf["iss"],
        "iat": timestamp,
        "exp": timestamp + cf["lifetime"],
        "aud": cf["aud"],
        "sub": "who knows?",
    }
    token = jwt.encode(
        payload, cf["key"], algorithm=cf["alg"]
    )
    _logger.info(f'Generated token with issuer {cf["iss"]}')
    resp = {
        "access_token": token
    }
    return resp


def decode_token(token):
    """validate a JWT

    This function is specified in the OpenAPI spec with
    `x-bearerInfoFunc: app.decode_token`, which is specifi to
    connexion.

    """

    header = jwt.get_unverified_header(token)
    iss = jwt.decode(
        token, algorithms=header["alg"], options={"verify_signature": False}
    )["iss"]

    if iss == "me":
        # this JWT claims to be from this API
        cf = config["jwt"]["api"]
    elif "auth0" in iss:
        # this JWT claims to be from auth0
        cf = config["jwt"]["auth0"]
    else:
        return 400, "Invalid JWT issuer"

    try:
        token_data = jwt.decode(token, algorithms=cf["alg"], key=cf["key"], audience=cf["aud"])
    except InvalidTokenError as e:
        raise Unauthorized(str(e)) from e

    # comply with RFC7662 re: token introspection
    # https://datatracker.ietf.org/doc/html/rfc7662#section-2.2
    token_data["active"] = True
    
    _logger.info(f"{token_data}")
    return token_data


def request_key(d):
    """compute a digest from a canonical form for the dictionary d"""

    j = json.dumps(d, sort_keys=True).encode("ascii")
    return hashlib.sha512(j).hexdigest()[:32]


def to_iso8601(ts):
    """convert timestamp float to iso8601 UTC time string"""
    return str(arrow.Arrow.utcfromtimestamp(ts))


#####################################################################
## API route handlers


def request_post(body, user):
    request = {
        "request": body,
        "sub": user
    }
    request_id = "QR-" + request_key(request)
    #if request_id in request_queue:
    #    return "Duplicate request ignored", 400
    request.update({
        "request_id": request_id,
        "submitted_at": arrow.utcnow().int_timestamp
    })

    # For this protoype, the queue is merely a dictionary
    # In a real deployment, we'd want a durable queue like AWS SWS
    request_queue[request_id] = request
    _logger.info(f"Created request {request_id}")

    return request


def request_get(request_id):
    try:
        request = request_queue[request_id]
    except KeyError:
        return "No such request_id", 404

    response = dict(
        request_id=request_id, 
        submitted_at=request["submitted_at"]
    )

    # For mocking purposes, transition the request at 60, 120, 180
    # seconds after submission.  Also, a FAILED status would usually be terminal.
    elapsed = arrow.utcnow().int_timestamp - request["submitted_at"]
    if elapsed < 60:
        response["status"] = "QUEUED"
    elif elapsed < 120:
        response["status"] = "RUNNING"
    elif elapsed < 180:
        response["status"] = "FAILED"
    else:
        response["status"] = "READY"
        response["report_json_uri"] = f"https://s3.blah/{request_id}/report.json"
        response["report_pdf_uri"] = f"https://s3.blah/{request_id}/report.pdf"
        response["finished_at"] = request["submitted_at"] + 180

    return response


app = connexion.App(__name__)
app.add_api("api.yaml", validate_responses=True)


if __name__ == "__main__":
    import coloredlogs
    coloredlogs.install(level="INFO")
    app.run(port=8080, debug=True, extra_files=["api.yaml"])
