#!/usr/bin/env python3
"""
MyOme external API, implemented with OpenAPI
"""

import enum
import hashlib
import json
import logging
import time
import uuid

import arrow
from cryptography.x509 import load_pem_x509_certificate
from jwt import decode, InvalidTokenError
from werkzeug.exceptions import Unauthorized
import connexion


request_queue = {}

_logger = logging.getLogger()


JWT_ALGORITHM = "RS256"
audience="https://api.myome.info/"
cert = b"""-----BEGIN CERTIFICATE-----
MIIDDTCCAfWgAwIBAgIJXZLOciXVhE+rMA0GCSqGSIb3DQEBCwUAMCQxIjAgBgNV
BAMTGWRldi00Y3JqanlieS51cy5hdXRoMC5jb20wHhcNMjIwMTA0MjExOTE0WhcN
MzUwOTEzMjExOTE0WjAkMSIwIAYDVQQDExlkZXYtNGNyamp5YnkudXMuYXV0aDAu
Y29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArkPSTIE+t13R5+RJ
2EqlYqKL4AuN7ysvzsOmRr2wjqfcQiYNrjDEmoZ2SIOBRrJoKr37ARC1Ok8pFx2n
Kt4nFCIny/BLt/H4HrloSgptCQhTNpm0TVD4JFP1vX7f0zxROz3uzVSCXRqA3Mhf
gwmdT+2wwY4833u2+rEAe/i1TmvFDz3245/IcfYuh+u48+3RXp3gu0Tkj2ifaeXh
jaJ4ckXn/V1iJeSCFFWfaj437kg2Gbgk16NDfU7e0AAiuHpWDHu4M74eOlI2D08r
kukf3MhTu1JjBSfkoFZ6rbHBXZjA05ocgODPPG5p0McL0056tMADIAAiqkQEmviw
onSCHwIDAQABo0IwQDAPBgNVHRMBAf8EBTADAQH/MB0GA1UdDgQWBBQm323tWic7
yIa3Hvh61szK0aA/FDAOBgNVHQ8BAf8EBAMCAoQwDQYJKoZIhvcNAQELBQADggEB
AJzPxyNTDPvty5z+RhBjPKmlE0VIOdY8fySZBdqMB57ZwqBZLjn0+tIBrksjcuma
kunIk/yVEV6D+YrYIi4feMaNdRLKnHj+uiAkieOwyoy6a6FyPFv57y45IENsw3Kd
aMBiLWenuLvz3zqTXw3bsLl+H31k8fqIUM4GGH479Oa2VjoP4c4G+xi44O56yY6m
dCWAOz4oamQB/F13/1NP/LC4RMx5jzKfNTKpymQqAlVkPkkiHuPiBCTkiTdHtN/f
zRYCwMWo8nsOORlMddcja6+SITSCD7cG1ZywxGsRhIoX9ccExkV0/J5LW8FiiYtU
sAebVN33HGGkT3ZTR4S2brw=
-----END CERTIFICATE-----
"""

cert_obj = load_pem_x509_certificate(cert)


def decode_token(token):
    """validate a JWT

    This function is specified in the OpenAPI spec with
    `x-bearerInfoFunc: app.decode_token`, which is specifi to
    connexion.

    """

    try:
        decoded = decode(token,
                         options={"verify_signature": False})
        return decode(token,
                          key=cert_obj.public_key(),
                          audience=audience,
                          algorithms=JWT_ALGORITHM)
    except InvalidTokenError as e:
        raise Unauthorized(str(e)) from e


def request_key(d):
    """compute a digest from a canonical form for the dictionary d

    """

    j = json.dumps(d, sort_keys=True).encode("ascii")
    return hashlib.sha512(j).hexdigest()[:32]

def to_iso8601(ts):
    """convert timestamp float to iso8601 UTC time string"""
    return str(arrow.Arrow.utcfromtimestamp(ts))


# route methods

def request_post(body):
    request_id = "QR-" + request_key(body)
    _logger.warn(f"{request_id} ({body})")
    if request_id in request_queue:
        return "Duplicate request ignored", 400
    request_queue[request_id] = {
        "submitted_at": arrow.utcnow().float_timestamp,
        "request": body
        }
    return {
        "request_id": request_id,
        }

def request_get(request_id):
    try:
        request = request_queue[request_id]
    except KeyError:
        return "No such request_id", 404

    response = dict(
        request_id = request_id,
        submitted_at = to_iso8601(request["submitted_at"])
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

