import json

import requests
import pandas as pd


def fetch_weather_data(dieter_url: str, latitude: float, longitude: float, access_token: str) -> tuple[pd.DataFrame, float, float]:
    """
    Fetches weather data from the openweathermap API.

    :param dieter_url:      The URL of the Dieter server.
    :param latitude:        The latitude of the location.
    :param longitude:       The longitude of the location.
    :param access_token:    The access token for the Dieter server.
    :return:
    """
    auth_header = f"Bearer {access_token}"
    headers = {"Authorization": auth_header}
    params = {"latlng": f"{latitude},{longitude}"}

    response = requests.get(dieter_url + "/try", headers=headers, params=params)

    body = response.json()
    try_data = body["_embedded"]["test_reference_year"][0]
    regionId = try_data["regionId"]
    regionName = try_data["regionName"]
    regionLat = try_data["regionLat"]
    regionLon = try_data["regionLng"]
    referenceYearSpan = try_data["referenceYearSpan"]
    fieldDescription = try_data["fieldDescription"]
    fieldData = try_data["fieldData"]

    df_weather = pd.read_json(json.dumps(fieldData), orient="records")

    return df_weather, regionLat, regionLon
