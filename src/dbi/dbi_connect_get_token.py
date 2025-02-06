from typing import cast
import json

import requests


def get_token(dbi_connect_url: str, secret: str, client: str) -> str:
    """
    Gets a token from the DBI Connect server.

    :param dbi_connect_url:     The URL of the DBI Connect server.
    :param secret:              The client secret.
    :param client:              The client ID.
    """
    data = {"grant_type": "client_credentials", "client_id": client, "client_secret": secret, "scope": ["profile", "email"]}
    data_serialized = json.dumps(data)

    # get token
    response = requests.post(dbi_connect_url + "/token", data=data_serialized, headers={"Content-Type": "application/json"})

    body = response.json()
    access_token = body.get("access_token", "")
    return cast(str, access_token)
