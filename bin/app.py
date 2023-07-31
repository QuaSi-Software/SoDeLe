import json

import pandas as pd
from shapely.geometry import Point, Polygon

import sodele
from sodele import simulatePVPlants


def readInTryData(latitude, longitude):
    """
    Reads in the try data.

    :param latitude:    The latitude.
    :type latitude:     float
    :param longitude:   The longitude.
    :type longitude:    float
    :return:    The try data.
    :rtype:     sodele.WeatherData
    """
    with open("./sodele/res/try/regionGeometry.json", "r") as f:
        regionGeometry = json.load(f)

    # check in which polygon the point is
    currentPoint = Point(longitude, latitude)
    currentPolygonID = None
    for regionData in regionGeometry["features"]:
        id = regionData["properties"]["id"]
        coordinates = regionData["geometry"]["coordinates"][0]
        polygon = Polygon(coordinates)
        if polygon.contains(currentPoint):
            currentPolygonID = id
            break

    # read in the weather data
    with open(f"./sodele/res/try/regions/TRY2035_{str(currentPolygonID).zfill(4)}_Jahr.dat", "r") as f:
        parsableData = ""
        for idx, line in enumerate(f.readlines()):
            if idx == 1:
                continue
            # strip whitespaces
            line = line.strip()
            # convert all whitespaces to single spaces
            line = " ".join(line.split())
            parsableData += line + "\n"
    # remove the last newline
    parsableData = parsableData[:-1]

    # convert the data to a dict
    data_dict = {}
    column_mapper = {}
    for idx, line in enumerate(parsableData.split("\n")):
        columns = line.split(" ")
        if idx == 0:
            for column_idx, column in enumerate(columns):
                column_mapper[column_idx] = column
                data_dict[column] = []
        else:
            for column_idx, column_value in enumerate(columns):
                column = column_mapper[column_idx]
                data_dict[column].append(float(column_value))

    df_weatherData = pd.DataFrame.from_dict(data_dict)

    # TODO: theese values are not correct
    rechtswert = 1
    hochwert = 1
    altitude = 1

    weatherData = sodele.WeatherData(
        rechtswert=rechtswert,
        hochwert=hochwert,
        altitude=altitude,
        kind="try",
        years=1,
        latitude=latitude,
        longitude=longitude,
        tz=1,
        adjustTimestamp=False,
        recalculateDNI=False,
        timeshiftInMinutes=0,
        df_weatherData=df_weatherData)

    return weatherData


def constructPVConfig():
    """
    Constructs the PV config.
    :return:
    """
    return sodele.PhotovoltaicConfig()


def constructPVPlants():
    """
    Constructs the PV plants.
    :return:
    """
    return [sodele.PhotovoltaicPlant()]


def main():
    weatherData = readInTryData(51.340199, 12.360103)
    pvConfig = constructPVConfig()
    pvPlants = constructPVPlants()
    sodeleInput = sodele.SodeleInput(pvConfig, pvPlants, weatherData)
    simulatePVPlants(sodeleInput)


if __name__ == "__main__":
    main()
