import json
import sys
import os
#import win32api
import pyproj                               # [MIT Licence] transformation of coordinates for DWD data
from geopy.geocoders import Nominatim       # [MIT Licence] get location from coordinates

import pvlib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from shapely.geometry import Point, Polygon

import sodele
from sodele import simulatePVPlants
from sodele.Helper.dictor import dictor
from sodele.Config import logging


def readInTryData(latitude, longitude):
    """
    Reads in the try data that has been predownload from "DWD Klimaberatungsmodule".

    :param latitude:    The latitude.
    :type latitude:     float
    :param longitude:   The longitude.
    :type longitude:    float
    :return:    The try data.
    :rtype:     sodele.WeatherData
    """
    with open("./src/sodele/res/try/regionGeometry.json", "r") as f:
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
    df_weatherData = readInDatFile_crawled(f"./src/sodele/res/try/regions/TRY2035_{str(currentPolygonID).zfill(4)}_Jahr.dat")

    # TODO: theese values are not correct! They are missing in the predownloaded crawled data! Should be added in near future!!!
    altitude = 200

    weatherData = sodele.WeatherData(
        altitude=altitude,
        kind="try",
        years=1,
        latitude=latitude,
        longitude=longitude,
        tz=1,
        adjustTimestamp=True,
        recalculateDNI=True,
        timeshiftInMinutes=30,
        df_weatherData=df_weatherData)

    logging().info("The weather data has been loaded from predownloaded DWD TRY files for Lat: " + str(latitude) + " and Long: '" + str(longitude) + " with " + str(df_weatherData.shape[0]) + " datapoints successfully.")

    return weatherData


def readInDatFile_crawled(datFile):
    # read in the weather data from predownloaded grid, files have no header
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

    df_data = pd.DataFrame.from_dict(data_dict)
    df_weatherData = pd.DataFrame()
    month = df_data["MM"]
    day = df_data["DD"]
    hour = df_data["HH"]
    df_weatherData["timeStamps"] = pd.to_datetime(dict(year=2035, month=month, day=day, hour=hour))  # ToDo: adjust year! This is not necessarily correct here! But information is not given in predownloaded TRY from DWD...
    df_weatherData.index = df_weatherData["timeStamps"]
    df_weatherData["temp_air"] = df_data["t"]
    df_weatherData["relative_humidity"] = df_data["RF"]
    df_weatherData["wind_speed"] = df_data["WG"]
    df_weatherData["atmospheric_pressure"] = df_data["p"] * 100  # convert hPa to Pa to be consistent with EPW
    df_weatherData["dhi"] = df_data["D"]      # diffus horizontal radiation, naming as in pvlib/EPW
    df_weatherData["ghi"] = df_weatherData["dhi"] + df_data["B"]   # global horizontal radiation = direct and diffuse horizontal radiation


    return df_weatherData



def readInDatFile(datFilePath):
    """
    Function reads in *.dat files from DWD TRY dataset (download from https://kunden.dwd.de/obt/)

    The timestamp of the result will always start at 01.01.2015 at 00:00 in order to be consistent with the alternative epw input data.
    Therefore, a realculation is needed with 30 Minute shift to start at 00:30 for correct results to account for the correct assignement of irradiation data and solar position. 

    Requirements on dat file:
    - has to be houly data with 8760 timesteps per datafile
    - Timezone has to be GMT+1 (MEZ)
    - irradiation data has to be average of the PAST hour prior to the current time stamp
    - beginning of the data block has to start with "***" to separate header from data

    The header of the -dat file has to be in the following structure:
    1 ...
    2 Rechtswert        : 3936500 Meter
    3 Hochwert          : 2449500 Meter
    4 Hoehenlage        : 450 Meter ueber NN 
    ...
    7 Art des TRY       : mittleres Jahr
    8 Bezugszeitraum    : 1995-2012
    ...

    The datablock of the .dat file has to be in the following structure:
    RW Rechtswert                                                    [m]       {3670500;3671500..4389500}
    HW Hochwert                                                      [m]       {2242500;2243500..3179500}
    MM Monat                                                                   {1..12}
    DD Tag                                                                     {1..28,30,31}
    HH Stunde (MEZ!)                                                           {1..24}
    t  Lufttemperatur in 2m Hoehe ueber Grund                        [GradC]
    p  Luftdruck in Standorthoehe                                    [hPa]
    WR Windrichtung in 10 m Hoehe ueber Grund                        [Grad]    {0..360;999}
    WG Windgeschwindigkeit in 10 m Hoehe ueber Grund                 [m/s]
    N  Bedeckungsgrad                                                [Achtel]  {0..8;9}
    x  Wasserdampfgehalt, Mischungsverhaeltnis                       [g/kg]
    RF Relative Feuchte in 2 m Hoehe ueber Grund                     [Prozent] {1..100}
    B  Direkte Sonnenbestrahlungsstaerke (horiz. Ebene)              [W/m^2]   abwaerts gerichtet: positiv
    D  Diffuse Sonnenbetrahlungsstaerke (horiz. Ebene)               [W/m^2]   abwaerts gerichtet: positiv
    A  Bestrahlungsstaerke d. atm. Waermestrahlung (horiz. Ebene)    [W/m^2]   abwaerts gerichtet: positiv
    E  Bestrahlungsstaerke d. terr. Waermestrahlung                  [W/m^2]   aufwaerts gerichtet: negativ
    IL Qualitaetsbit bezueglich der Auswahlkriterien                           {0;1;2;3;4}
    
    Output:
    - DataFrame with [0] header data and [1] weather data
    - coordinates will be transformes in standard WGS 84 system and writte to header data
    - air pressure will be changed from hPa to Pa in accordance of pvlib convention

    """
    # read in the weather data in .dat weather file format as it comes from the DWD website
    # open file
    try:
        datfile = open(str(datFilePath), 'r')
    except Exception as e: 
        raise ValueError(f"Could not read in the .dat weather data file {datFilePath}. The following error occured: " + str(e))

    # read metadata from header
    metadata = dict()
    currentline = 0
    for line in datfile:
        # read in line by line of header
        row = line.rstrip().split(":",1)
        
        # assine header data to header dict if needed
        try:
            if currentline == 1:
                value = int(row[1].split()[0])
                metadata['Rechtswert'] = value
            elif currentline == 2:
                value = int(row[1].split()[0])
                metadata['Hochwert'] = value
            elif currentline == 3:
                value = float(row[1].split()[0])
                metadata['altitude'] = value
            elif currentline == 6:
                value = str(row[1])
                metadata['kind'] = value
            elif currentline == 7:
                value = str(row[1])
                metadata['years'] = value
            elif currentline == 32: # get column names for data as between column names and data is a separator line (***)
                columnnames = row[0].split()
        except Exception as e: 
            raise ValueError(f"Could not read in the header of .dat weather data file {datFilePath}. The following error occured: " + str(e))

        currentline += 1

        # beak loop of reding the header if data block has startet. Begin of data has to start with "***""
        if row[0] == '***':
            break

    # calculate latitude and longitude from Hochwert and Rechtswert from header
    # using pyproj from https://github.com/pyproj4/pyproj (MIT license)
    inProj = 'EPSG:3034'  # Input Projection: EPSG system used by DWD for TRY data (Lambert-konforme konische Projektion)
    outProj = 'EPSG:4326'  # Output Projection: World Geodetic System 1984 (WGS 84) 
    transformer = pyproj.Transformer.from_crs(inProj, outProj)
    lat, lon = transformer.transform(metadata['Hochwert'], metadata['Rechtswert'])

    # write position information to metadata dict
    metadata['latitude'] = lat
    metadata['longitude'] = lon
    metadata['TZ'] = 1   

    # read data points
    # already used readline above, therefore no rows has to be skipped here!
    try:                  
        dat_data = pd.read_table(datfile, header=None, names=columnnames, delim_whitespace=True)
    except Exception as e: 
        raise ValueError(f"Could not read the datapoints in the .dat weather data file {datFilePath}. The following error occured: " + str(e))
   
    if dat_data.shape[0] != 8760:
        raise ValueError(f"Could not read in the .dat weather data file {datFilePath}. "  + str(dat_data.shape[0]) + " datapoints has been read in instead of 8760. Checke the .dat file and make sure, that the datapoints begin with ""***""!" )

    # create index that supplies correct date and time zone information
    # using 2015 as reference year and starting at 00:00 --> set to 00:30 for correct results!!! But in order to get constistency with epw, 00:00 is chosen.
    dat_data.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='H', tz=int(metadata['TZ']*60*60)))  #tz in seconds with respect to GMT

    # adjust units 
    dat_data["p"] = dat_data["p"] * 100  # convert hPa to Pa to be consistent with EPW
    
    df_weatherData = pd.DataFrame()
    df_weatherData.index = dat_data.index
    df_weatherData["temp_air"] = dat_data["t"]
    df_weatherData["relative_humidity"] = dat_data["RF"]
    df_weatherData["wind_speed"] = dat_data["WG"]
    df_weatherData["atmospheric_pressure"] = dat_data["p"]
    df_weatherData["dhi"] = dat_data["D"]      # diffus horizontal radiation, naming as in pvlib/EPW
    df_weatherData["ghi"] = df_weatherData["dhi"] + dat_data["B"]   # global horizontal radiation = direct and diffuse horizontal radiation

    return df_weatherData, metadata


def readInEPWFile(epwFile):
    df_weather, metadata = pvlib.iotools.read_epw(epwFile)
    year = df_weather["year"]
    month = df_weather["month"]
    day = df_weather["day"]
    hour = df_weather["hour"]
    df_weather["timeStamps"] = pd.to_datetime(dict(year=year, month=month, day=day, hour=hour))

    logging().info("The EPW weather file '" + str(epwFile) + "' with " + str(df_weather.shape[0]) + " datapoints was read in successfully.")

    return sodele.WeatherData(
        altitude=metadata["altitude"],
        kind="epw",
        years=1,
        latitude=metadata["latitude"],
        longitude=metadata["longitude"],
        tz=metadata["TZ"],
        adjustTimestamp=True,
        recalculateDNI=True,
        timeshiftInMinutes=30,
        df_weatherData=df_weather)


def readInWeatherDataFile(weatherDataFile):
    if weatherDataFile.endswith(".dat"):
        df_weatherData, metadata = readInDatFile(weatherDataFile)

        logging().info("The DWD .dat weather file '" + str(weatherDataFile) + "' of kind '" + str(metadata['kind'])[1:] + "' from the years" + str(metadata['years']) + " with " + str(df_weatherData.shape[0]) + " datapoints was read in successfully.")
        
        return sodele.WeatherData(
            altitude=metadata["altitude"],
            kind=metadata['kind'] + " of the years " + metadata['years'] ,
            years=1,
            latitude=metadata["latitude"],
            longitude=metadata["longitude"],
            tz=metadata["TZ"],
            adjustTimestamp=True,
            recalculateDNI=True,
            timeshiftInMinutes=30,
            df_weatherData=df_weatherData)

    elif weatherDataFile.endswith(".epw"):
        return readInEPWFile(weatherDataFile)
    else:
        raise ValueError(f"Could not read in the weather data file {weatherDataFile}.")


def visualizePVPlants(energyProfiles, energyAreaProfiles, resultPath, showPlot):
    # ToDo: immprove figures so that they respresent the old figures!

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


# Functino to receive location information and print them to the log
def print_location_information(latitude, longitude):
    # print location info of weather file
    logging().info("-----")
    logging().info("The coordinates given in the provided .dat-file or as input value are:")
    logging().info("Latitude: " + str(latitude))
    logging().info("Longitude: " + str(longitude))

    # get location name using geopy (https://github.com/geopy/geopy) (MIT License)
    try:
        geolocator = Nominatim(user_agent="Sodele")
        location = geolocator.reverse(str(latitude) + "," + str(longitude))
        address = location.raw['address']

        # find city, town, village or hamlet name
        if isinstance(address.get('city'), str):
            if isinstance(address.get('suburb'), str):
                city = (address.get('city') + ' - ' + address.get('suburb') )
            elif isinstance(address.get('city_district'), str):
                city = (address.get('city') + ' - ' + address.get('city_district') )
            else:
                city = address.get('city')
        elif isinstance(address.get('town'), str):
            city = address.get('town')
        elif isinstance(address.get('village'), str):
            city = address.get('village')
        elif isinstance(address.get('hamlet'), str):
            city = address.get('hamlet')
        else:
            city = 'unknown city'

        if isinstance(address.get('postcode'), str):
            logging().info('City: ' + address.get('postcode') + ' ' + city )
        else:
             logging().info('City: ' + city )
        if isinstance(address.get('state'), str):
            logging().info('State: ' + address.get('state'))
        if isinstance(address.get('country'), str):
            logging().info('Country: ' + address.get('country'))
    except Exception as e:
        logging().info("Detailed information on the location could not be received from the online server...")
        logging().info('Error message: ' + str(e))

    logging().info("-----")

    return


def main(inputJson: dict, filePath):
    latitude = dictor(inputJson, "weatherData.latitude")
    longitude = dictor(inputJson, "weatherData.longitude")
    weatherDataFile = dictor(inputJson, "weatherData.weatherDataFile")
    if weatherDataFile is not None:
        weatherData = readInWeatherDataFile(weatherDataFile)  # .dat or .epw file externally given by absolute or relative path
    else:
        weatherData = readInTryData(latitude, longitude) # modified .dat file crawled from DWD and saved locally
    inputJson["weatherData"] = weatherData.serialize()
    sodeleInput = sodele.SodeleInput.deserialize(inputJson)

    print_location_information(weatherData.latitude, weatherData.longitude)

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
    #pathToInputJson = sys.argv[1]
    pathToInputJson = "./docs/testInput.json"
    #pathToInputJson = "./dist/231023_13-36-37.json"

    if not os.path.exists(pathToInputJson):
        raise FileNotFoundError(f"Could not find the input json at {pathToInputJson}")
    with open(pathToInputJson, "r") as f:
        inputJson = json.load(f)
    main(inputJson, filePath=pathToInputJson)
