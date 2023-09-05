import json
import sys
import os

import pvlib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from shapely.geometry import Point, Polygon

import sodele
from sodele import simulatePVPlants
from sodele.Helper.dictor import dictor


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
    df_weatherData = readInDatFile(f"./sodele/res/try/regions/TRY2035_{str(currentPolygonID).zfill(4)}_Jahr.dat")

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


def readInDatFile(datFile):
    # read in the weather data
    with open(datFile, "r") as f:
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
    month = df_weatherData["MM"]
    day = df_weatherData["DD"]
    hour = df_weatherData["HH"]
    df_weatherData["timeStamps"] = pd.to_datetime(dict(year=2035, month=month, day=day, hour=hour))
    df_weatherData["temp_air"] = df_weatherData["t"]
    df_weatherData["relative_humidity"] = df_weatherData["RF"]
    df_weatherData["wind_speed"] = df_weatherData["WG"]
    df_weatherData["atmospheric_pressure"] = df_weatherData["p"]
    df_weatherData["dhi"] = df_weatherData["B"]
    df_weatherData["ghi"] = df_weatherData["dhi"] + df_weatherData["D"]

    return df_weatherData


def readInEPWFile(epwFile):
    df_weather, metadata = pvlib.iotools.read_epw(epwFile)
    year = df_weather["year"]
    month = df_weather["month"]
    day = df_weather["day"]
    hour = df_weather["hour"]
    df_weather["timeStamps"] = pd.to_datetime(dict(year=year, month=month, day=day, hour=hour))

    rechtswert = 1
    hochwert = 1

    return sodele.WeatherData(
        rechtswert=rechtswert,
        hochwert=hochwert,
        altitude=metadata["altitude"],
        kind="epw",
        years=1,
        latitude=metadata["latitude"],
        longitude=metadata["longitude"],
        tz=metadata["TZ"],
        adjustTimestamp=False,
        recalculateDNI=False,
        timeshiftInMinutes=0,
        df_weatherData=df_weather)


def readInWeatherDataFile(weatherDataFile, latitude, longitude):
    if weatherDataFile.endswith(".dat"):
        df_weatherData = readInDatFile(weatherDataFile)

        rechtswert = 1
        hochwert = 1
        altitude = 1

        return sodele.WeatherData(
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

    elif weatherDataFile.endswith(".epw"):
        return readInEPWFile(weatherDataFile)
    else:
        raise ValueError(f"Could not read in the weather data file {weatherDataFile}.")


def visualizePVPlants(energyProfiles, energyAreaProfiles, resultPath, showPlot=False):
    # create indviaul plots for each plant
    numberOfPlants = len(energyProfiles) - 1
    maxEnergyValue = max([max(energyProfile) for energyProfile in energyProfiles[:numberOfPlants]])
    maxAreaValue = max([max(energyAreaProfile) for energyAreaProfile in energyAreaProfiles[:numberOfPlants]])

    def createSinglePlot(energyProfile, energyAreaProfile, name):
        numberOfTimeSteps = len(energyProfile)
        # create an x axis in hours and create a datetime object for each time step
        x = [i for i in range(numberOfTimeSteps)]
        x = pd.to_datetime(x, unit="h", origin="2020-01-01")

        # create the plot
        fig, ax = plt.subplots(figsize=(32, 8))
        df_energyProfile = pd.DataFrame({"timeStamps": x,
                                         "Energy Profile (kWh)": energyProfile,
                                         "Energy Area Profile (kWh/m2)": energyAreaProfile
                                         })
        sns.lineplot(x="timeStamps", y="Energy Profile (kWh)", data=df_energyProfile, ax=ax, color="blue")
        sns.lineplot(x="timeStamps", y="Energy Area Profile (kWh/m2)", data=df_energyProfile, ax=ax, color="red")
        ax.set_ylim(0, maxEnergyValue * 1.1)
        ax.set_xlim(x[0], x[-1])
        ax.set_title(f"Energy Profile of Plant {plantNumber}")
        ax.set_xlabel("Time")
        ax.set_ylabel("Energy (kWh)")
        ax.legend(["Energy Profile (kWh)", "Energy Area Profile (kWh/m2)"])
        plt.savefig(f"{resultPath}/{name}.png")
        if showPlot:
            plt.show()
        plt.close()

    for plantNumber in range(numberOfPlants):
        energyProfile = energyProfiles[plantNumber]
        energyAreaProfile = energyAreaProfiles[plantNumber]
        createSinglePlot(energyProfile, energyAreaProfile, f"energyProfile_{plantNumber}")

    energyProfileSummary = energyProfiles[-1]
    energyAreaProfileSummary = energyAreaProfiles[-1]
    createSinglePlot(energyProfileSummary, energyAreaProfileSummary, "energyProfileSummary")

    # create a plot for the summary of all plants
    df_energyProfileSummary = pd.DataFrame(columns=["timeStamps", "Data", "PV Plant", "Is Area"])
    for plantNumber in range(len(energyProfiles)):
        name = f"Plant {plantNumber}: "
        if plantNumber == len(energyProfiles) - 1:
            name = "Summary of all Plants: "
        numberOfTimeSteps = len(energyProfileSummary)
        # create an x axis in hours and create a datetime object for each time step
        x = [i for i in range(numberOfTimeSteps)]
        x = pd.to_datetime(x, unit="h", origin="2020-01-01")
        df_tmp = pd.DataFrame({"timeStamps": x,
                               "Data": energyProfiles[plantNumber],
                               "PV Plant": f"{name} Energy Profile",
                               "Is Area": False})
        df_energyProfileSummary = pd.concat([df_energyProfileSummary, df_tmp], axis=0)

        df_tmp = pd.DataFrame({"timeStamps": x,
                               "Data": energyAreaProfiles[plantNumber],
                               "PV Plant": f"{name} Energy Area Profile",
                               "Is Area": True})
        df_energyProfileSummary = pd.concat([df_energyProfileSummary, df_tmp], axis=0)

    fig, ax = plt.subplots(figsize=(32, 8))
    sns.lineplot(x="timeStamps", y="Data", hue="PV Plant", data=df_energyProfileSummary, ax=ax)
    ax.set_xlim(x[0], x[-1])
    ax.set_title("Summary of all Energy Profiles")
    ax.set_xlabel("Time")
    ax.set_ylabel("Energy (kWh)")
    plt.savefig(f"{resultPath}/energyProfileTotal.png")
    if showPlot:
        plt.show()
    plt.close()


def main(inputJson: dict, filePath):
    latitude = dictor(inputJson, "weatherData.latitude")
    longitude = dictor(inputJson, "weatherData.longitude")
    weatherDataFile = dictor(inputJson, "weatherData.weatherDataFile")
    if weatherDataFile is not None:
        weatherData = readInWeatherDataFile(weatherDataFile, latitude, longitude)
    else:
        weatherData = readInTryData(latitude, longitude)
    inputJson["weatherData"] = weatherData.serialize()
    sodeleInput = sodele.SodeleInput.deserialize(inputJson)
    result = simulatePVPlants(sodeleInput)

    energyProfiles = []
    energyAreaProfiles = []

    for pvResult in result["PhotovoltaicResults"]["PhotovoltaicPlants"]:
        energyProfiles.append(pvResult["EnergyProfile"])
        energyAreaProfiles.append(pvResult["EnergyAreaProfile"])

    energyProfiles.append(result["PhotovoltaicResults"]["SummaryOfAllPlants"]["EnergyProfile"])
    energyAreaProfiles.append(result["PhotovoltaicResults"]["SummaryOfAllPlants"]["EnergyAreaProfile"])

    # remove the .json from the filePath
    basePath = filePath[:-5]
    resultPath = basePath + "_result"
    # create folder for the results
    if not os.path.exists(resultPath):
        os.makedirs(resultPath)

    # save the result
    with open(resultPath + "/result.json", "w") as f:
        json.dump(result, f, indent=4)

    visualizePVPlants(energyProfiles, energyAreaProfiles, resultPath, sodeleInput.showPlots)


if __name__ == "__main__":
    # get the path to the input json from argv
    # pathToInputJson = sys.argv[1]
    pathToInputJson = "./docs/testInput.json"
    if not os.path.exists(pathToInputJson):
        raise FileNotFoundError(f"Could not find the input json at {pathToInputJson}")
    with open(pathToInputJson, "r") as f:
        inputJson = json.load(f)
    main(inputJson, filePath=pathToInputJson)
