import json

import requests


def get_token(url, secret, client):
    """
    Gets a token from the DBI Connect server.
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": client,
        "client_secret": secret,
        "scope": ["profile", "email"]
    }
    data = json.dumps(data)

    # get token
    response = requests.post(url + "/token",
                             data=data,
                             headers={"Content-Type": "application/json"})

    try:
        body = response.json()
        access_token = body["access_token"]
        return access_token
    except Exception as e:
        raise exceptions.Unauthorized()
