#!/usr/bin/env python3
"""
Partner API demonstration using OpenAPI, JWT, and Connexion+Flask.
"""

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
    timestamp = arrow.utcnow().float_timestamp
    cf = jwt_config["api"]
    payload = {
        "iss": cf["iss"],
        "iat": int(timestamp),
        "exp": int(timestamp + cf["lifetime"]),
        "aud": cf["aud"],
        "sub": cf["iss"],
    }
    token = jwt.encode(
        payload, cf["key"], algorithm=cf["alg"]
    )
    _logger.info(f'Generated token with issuer {cf["iss"]}')
    return token


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

    _logger.info(f"{token=}")
    _logger.info(f"{iss=}")
    _logger.info(f"{cf['alg']=}")
    _logger.info(f"{cf['key']=}")
    _logger.info(f"{cf['aud']=}")

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
    request = dict(
        body = body,
        sub = user,
    )
    request_id = "QR-" + request_key(body)
    if request_id in request_queue:
        return "Duplicate request ignored", 400
    request.update(dict(
        request_id = request_id,
        submitted_at = arrow.utcnow().float_timestamp    
    ))
    request_queue[request_id] = request
    return {
        "request_id": request_id,
    }


def request_get(request_id):
    try:
        request = request_queue[request_id]
    except KeyError:
        return "No such request_id", 404

    response = dict(
        request_id=request_id, submitted_at=to_iso8601(request["submitted_at"])
    )

    elapsed = arrow.utcnow().float_timestamp - request["submitted_at"]

    # For mocking purposes, transition the request at 15, 30, and 45
    # seconds after submission.
    if elapsed < 5:
        response["status"] = "QUEUED"
    elif elapsed < 10:
        response["status"] = "RUNNING"
    elif elapsed < 15:
        response["status"] = "FAILED"
    else:
        response["status"] = "READY"
        response["report_json_uri"] = f"https://s3.blah/{request_id}/report.json"
        response["report_pdf_uri"] = f"https://s3.blah/{request_id}/report.pdf"
        response["finished_at"] = to_iso8601(request["submitted_at"] + 15)

    return response


app = connexion.App(__name__)
app.add_api("api.yaml", validate_responses=True)


if __name__ == "__main__":
    import coloredlogs

    coloredlogs.install(level="INFO")
    app.run(port=8080, debug=True)
