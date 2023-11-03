import json

import requests


def get_token(dbi_connect_url, secret, client):
    """
    Gets a token from the DBI Connect server.

    :param dbi_connect_url:     The URL of the DBI Connect server.
    :param secret:              The client secret.
    :param client:              The client ID.
    """
    data = {
        "grant_type": "client_credentials",
        "client_id": client,
        "client_secret": secret,
        "scope": ["profile", "email"]
    }
    data = json.dumps(data)

    # get token
    response = requests.post(dbi_connect_url + "/token",
                             data=data,
                             headers={"Content-Type": "application/json"})

    body = response.json()
    access_token = body["access_token"]
    return access_token
