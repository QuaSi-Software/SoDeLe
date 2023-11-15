import json
import os
import sys

import dotenv
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import pvlib
import pyproj  # [MIT Licence] transformation of coordinates for DWD data
import seaborn as sns
from geopy.geocoders import Nominatim  # [MIT Licence] get location from coordinates

import sodele
from dbi.dbi_connect_get_token import get_token
from dbi.dbi_fetch_weather_data import fetch_weather_data
from sodele import simulatePVPlants
from sodele.Config import logging
from sodele.Helper.dictor import dictor

# load the .env file
dotenv.load_dotenv()


def requestTryData(latitude, longitude):
    """
    Requests in the try data that has been predownload from "DWD Klimaberatungsmodule".

    :param latitude:    The latitude.
    :type latitude:     float
    :param longitude:   The longitude.
    :type longitude:    float
    :return:    The try data.
    :rtype:     sodele.WeatherData
    """
    DBI_CONNECT_URL = os.getenv('DBI_CONNECT_URL', "")
    DBI_CONNECT_CLIENT_ID = os.getenv('DBI_CONNECT_CLIENT_ID', "")
    DBI_CONNECT_CLIENT_SECRET = os.getenv('DBI_CONNECT_CLIENT_SECRET', "")

    DBI_DIETER_URL = os.getenv('DBI_DIETER_URL', "")

    access_token = get_token(DBI_CONNECT_URL, DBI_CONNECT_CLIENT_SECRET, DBI_CONNECT_CLIENT_ID)
    df_weatherData, latitude, longitude = fetch_weather_data(DBI_DIETER_URL, latitude, longitude, access_token)
    month = df_weatherData["MM"]
    day = df_weatherData["DD"]
    hour = df_weatherData["HH"]

    # adjust units
    df_weatherData["p"] = df_weatherData["p"] * 100  # convert hPa to Pa to be consistent with EPW

    df_weatherData.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='H', tz=int(1 * 60 * 60)))
    df_weatherData["temp_air"] = df_weatherData["t"]
    df_weatherData["relative_humidity"] = df_weatherData["RF"]
    df_weatherData["wind_speed"] = df_weatherData["WG"]
    df_weatherData["atmospheric_pressure"] = df_weatherData["p"]
    df_weatherData["dhi"] = df_weatherData["D"]  # diffus horizontal radiation, naming as in pvlib/EPW
    df_weatherData["ghi"] = df_weatherData["dhi"] + df_weatherData["B"]  # global horizontal radiation = direct and diffuse horizontal radiation

    weatherData = sodele.WeatherData(
        altitude=0,
        kind="try",
        years=1,
        latitude=latitude,
        longitude=longitude,
        tz=1,
        adjustTimestamp=True,
        recalculateDNI=True,
        timeshiftInMinutes=30,
        df_weatherData=df_weatherData)

    logging().info(f"The weather data has been loaded from predownloaded DWD TRY files for Lat: '{latitude}' and Long: '{longitude}' with {df_weatherData.shape[0]} datapoints successfully.")

    return weatherData


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
        row = line.rstrip().split(":", 1)

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
            elif currentline == 32:  # get column names for data as between column names and data is a separator line (***)
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
        raise ValueError(f"Could not read in the .dat weather data file {datFilePath}. " + str(dat_data.shape[0]) + " datapoints has been read in instead of 8760. Checke the .dat file and make sure, that the datapoints begin with ""***""!")

    # create index that supplies correct date and time zone information
    # using 2015 as reference year and starting at 00:00 --> set to 00:30 for correct results!!! But in order to get constistency with epw, 00:00 is chosen.
    dat_data.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='H', tz=int(metadata['TZ'] * 60 * 60)))  # tz in seconds with respect to GMT

    # adjust units 
    dat_data["p"] = dat_data["p"] * 100  # convert hPa to Pa to be consistent with EPW

    df_weatherData = pd.DataFrame()
    df_weatherData.index = dat_data.index
    df_weatherData["temp_air"] = dat_data["t"]
    df_weatherData["relative_humidity"] = dat_data["RF"]
    df_weatherData["wind_speed"] = dat_data["WG"]
    df_weatherData["atmospheric_pressure"] = dat_data["p"]
    df_weatherData["dhi"] = dat_data["D"]  # diffus horizontal radiation, naming as in pvlib/EPW
    df_weatherData["ghi"] = df_weatherData["dhi"] + dat_data["B"]  # global horizontal radiation = direct and diffuse horizontal radiation

    return df_weatherData, metadata


def readInEPWFile(epwFile):
    df_weather, metadata = pvlib.iotools.read_epw(epwFile)
    year = df_weather["year"]
    month = df_weather["month"]
    day = df_weather["day"]
    hour = df_weather["hour"]
    df_weather["timeStamps"] = pd.to_datetime(dict(year=year, month=month, day=day, hour=hour))

    logging().info(f"The EPW weather file '{epwFile}' with {df_weather.shape[0]} datapoints was read in successfully.")

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


        logging().info(f"The DWD .dat weather file '{weatherDataFile}' of kind '{metadata['kind'][1:]}' from the years {metadata['years']} with {df_weatherData.shape[0]} datapoints was read in successfully.")

        return sodele.WeatherData(
            altitude=metadata["altitude"],
            kind=metadata['kind'] + " of the years " + metadata['years'],
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


def visualizePVPlants(energyProfiles, energyAreaProfiles, resultPath, showPlot, plantEnergyKWPSum, plantAreaTotal, plantPowerTotal, plantEnergySum):
    fignum = 0
    def create_hourly_plot(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, max_value=None, with_text=True):
        nonlocal fignum 
        # Create a barplot of the data
        plt.figure(fignum)
        fignum += 1
        sns.lineplot(data=df_data, x=df_data.index, y=df_data.columns[col_idx], color=color)
        plt.title(f"PV-Leistungsprofil für PV-Anlage {col_idx}")
        plt.xlabel('Zeitschritte im Jahr (entspricht Zeitschrittweite des Wetterdatensatzes)')
        plt.ylabel('el. Leistung gemittelt über Zeitschritt [kW]')

        if max_value is None:
            max_value = df_data.iloc[:, col_idx].max()

        # set the y axis range from 0-1.1 times the max value
        plt.ylim(0, max_value * 1.1)
        # set the x axis range from
        # write some text to the topleft
        if with_text:
            plt.text(0.01, 0.99, f"PV-Ertrag: {sum_pv:,.0f}".replace(",", ".") + " kWh", transform=plt.gca().transAxes, verticalalignment='top')
            plt.text(0.01, 0.95, f"PV-Ertrag: {sum_pv_power:,.0f}".replace(",", ".") + " kWh/kWp", transform=plt.gca().transAxes, verticalalignment='top')
            plt.text(0.01, 0.91, f"PV-Ertrag: {sum_pv_area:,.0f}".replace(",", ".") + " kWh/(m² a)", transform=plt.gca().transAxes, verticalalignment='top')

    def create_aggregated_plot(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, aggregation, labels, rot=0, max_value=None, with_text=True):
        nonlocal fignum
        df_data = df_data.resample(aggregation).sum()
        # Create a barplot of the data
        plt.figure(fignum)
        fignum += 1
        sns.barplot(data=df_data, x=df_data.index, y=df_data.columns[col_idx], color=color)
        plt.title(f"PV-Leistungsprofil für PV-Anlage {col_idx}")
        plt.xlabel('Zeitschritte im Jahr')
        plt.ylabel('el. Leistung gemittelt über Zeitschritt [kW]')

        if max_value is None:
            max_value = df_data.iloc[:, col_idx].max()

        # set the y axis range from 0-1.1 times the max value
        plt.ylim(0, max_value * 1.1)
        # set the x axis range from
        # write some text to the topleft
        if with_text:
            plt.text(0.01, 0.99, f"PV-Ertrag: {sum_pv:,.0f}".replace(",", ".") + " kWh", transform=plt.gca().transAxes, verticalalignment='top')
            plt.text(0.01, 0.95, f"PV-Ertrag: {sum_pv_power:,.0f}".replace(",", ".") + " kWh/kWp", transform=plt.gca().transAxes, verticalalignment='top')
            plt.text(0.01, 0.91, f"PV-Ertrag: {sum_pv_area:,.0f}".replace(",", ".") + " kWh/(m² a)", transform=plt.gca().transAxes, verticalalignment='top')

        # set the xticks to the labels
        plt.xticks(range(len(df_data.index)), labels)
        # rotate the labels
        plt.xticks(rotation=rot)

    def create_hourly_plot_summed(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, max_value=None):
        nonlocal fignum
        create_hourly_plot(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, max_value=max_value, with_text=False)
        plt.title("Summiertes PV-Energieprofil aller PV-Anlagen")
        plt.ylabel("Energieprofil [kW]")

        # set the x axis range from
        # write some text to the topleft
        plt.text(0.01, 0.99, f"PV-Ertrag aller PV-Anlagen: {sum_pv:,.0f}".replace(",", ".") + " kWh", transform=plt.gca().transAxes, verticalalignment='top')
        plt.text(0.01, 0.95, f"PV-Ertrag aller PV-Anlagen: {sum_pv_power:,.0f}".replace(",", ".") + " kWh/kWp", transform=plt.gca().transAxes, verticalalignment='top')
        plt.text(0.01, 0.91, f"PV-Ertrag aller PV-Anlagen: {sum_pv_area:,.0f}".replace(",", ".") + " kWh/(m² a)", transform=plt.gca().transAxes, verticalalignment='top')

    def create_aggregated_plot_summed(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, aggregation, labels, rot=0, max_value=None):
        nonlocal fignum
        create_aggregated_plot(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, aggregation, labels, rot=rot, max_value=max_value, with_text=False)
        plt.title(f"Summiertes PV-Energieprofil aller PV-Anlagen")
        plt.ylabel('Energieprofil [kW]')

        # set the x axis range from
        # write some text to the topleft#
        plt.text(0.01, 0.99, f"PV-Ertrag aller PV-Anlagen: {sum_pv:,.0f}".replace(",", ".") + " kWh", transform=plt.gca().transAxes, verticalalignment='top')
        plt.text(0.01, 0.95, f"PV-Ertrag aller PV-Anlagen: {sum_pv_power:,.0f}".replace(",", ".") + " kWh/kWp", transform=plt.gca().transAxes, verticalalignment='top')
        plt.text(0.01, 0.91, f"PV-Ertrag aller PV-Anlagen: {sum_pv_area:,.0f}".replace(",", ".") + " kWh/(m² a)", transform=plt.gca().transAxes, verticalalignment='top')

    def create_hourly_compare_plot(df_data, color_map):
        nonlocal fignum
        columns = df_data.columns
        used_columns = columns[:-1]
        df_data = df_data[used_columns]
        # melt to create a comparison plot
        df_data = df_data.melt(ignore_index=False)
        # rename the "variable" column to "PV-Anlage"
        df_data = df_data.rename(columns={"variable": "PV-Anlage"})
        # Create a barplot of the data
        plt.figure(fignum)
        fignum += 1
        sns.lineplot(data=df_data, x=df_data.index, y="value", hue="PV-Anlage", palette=color_map)
        plt.title("Vergleich PV-Energieprofil aller PV-Anlagen")
        plt.xlabel('Zeitschritte im Jahr (entspricht Zeitschrittweite des Wetterdatensatzes)')
        plt.ylabel('Energieprofil [kW]')

        max_value = df_data['value'].max()

        # set the y axis range from 0-1.1 times the max value
        plt.ylim(0, max_value * 1.1)

    def create_aggregated_compare_plot(df_data, color_map, aggregation, labels, rot=0):
        nonlocal fignum
        df_data = df_data.resample(aggregation).sum()
        columns = df_data.columns
        used_columns = columns[:-1]
        df_data = df_data[used_columns]
        # melt to create a comparison plot
        df_data = df_data.melt(ignore_index=False)

        # rename the "variable" column to "PV-Anlage"
        df_data = df_data.rename(columns={"variable": "PV-Anlage"})
        # Create a barplot of the data
        plt.figure(fignum)
        fignum += 1
        sns.barplot(data=df_data, x=df_data.index, y="value", hue="PV-Anlage", palette=color_map)
        plt.title("Vergleich PV-Energieprofil aller PV-Anlagen")
        plt.xlabel('Zeitschritte im Jahr')
        plt.ylabel('el. Leistung gemittelt über Zeitschritt [kW]')

        max_value = df_data['value'].max()

        # set the y axis range from 0-1.1 times the max value
        plt.ylim(0, max_value * 1.1)

        # set the xticks to the labels
        plt.xticks(range(len(labels)), labels)
        # rotate the labels
        plt.xticks(rotation=rot)

    # create individual plots for each plant
    numberOfPlants = len(energyProfiles) - 1
    columns = [f"PV_Plant_{i}" for i in range(numberOfPlants)] + ["Summary of all Plants"]

    df_energyProfileSummary = pd.DataFrame()
    df_areaProfileSummary = pd.DataFrame()
    df_energyProfileSummary.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='H'))  # tz in seconds with respect to GMT
    df_areaProfileSummary.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='H'))  # tz in seconds with respect to GMT
    for idx, col in enumerate(columns):
        # add the data to the dataframe
        df_energyProfileSummary[col] = energyProfiles[idx]
        df_areaProfileSummary[col] = energyAreaProfiles[idx]

    # set the global pplot to 16x9
    plt.rcParams['figure.figsize'] = [21, 9]
    sns.set_style("whitegrid")

    color_map = {}
    number_of_colors = len(df_energyProfileSummary.columns)
    for i, col in enumerate(df_energyProfileSummary.columns):
        if i == (number_of_colors - 1):
            color_map[col] = matplotlib.colormaps.get_cmap('tab20')(0)
        else:
            color_map[col] = matplotlib.colormaps.get_cmap('tab20')(i + 1)

    number_of_pv = len(df_energyProfileSummary.columns) - 1
    max_value_hourly = 0
    max_value_monthly = 0
    max_value_weekly = 0
    for pv_plant_idx in range(number_of_pv):
        max_value_hourly = max(max_value_hourly, df_energyProfileSummary.iloc[:, pv_plant_idx].max())
        df_weekly = df_energyProfileSummary.resample('W').sum()
        df_monthly = df_energyProfileSummary.resample('M').sum()
        max_value_weekly = max(max_value_weekly, df_weekly.iloc[:, pv_plant_idx].max())
        max_value_monthly = max(max_value_monthly, df_monthly.iloc[:, pv_plant_idx].max())

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weeks = [f"KW {i}" for i in range(1, 54)]

    for pv_plant_idx in range(number_of_pv):
        sum_pv_energy_power_rel = plantEnergyKWPSum[pv_plant_idx]
        sum_pv_energy_area_related = df_areaProfileSummary.iloc[:, pv_plant_idx].sum()
        sum_pv_energy = plantEnergySum[pv_plant_idx]
        color = color_map[df_energyProfileSummary.columns[pv_plant_idx]]
        create_hourly_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil für PV-Anlage {pv_plant_idx}.png")

        create_aggregated_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'M', months, rot=-45)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil für PV-Anlage {pv_plant_idx} aggregated per month.png")
        #close and dont show the plot
        plt.close()

        create_aggregated_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'W', weeks, rot=-45)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil für PV-Anlage {pv_plant_idx} aggregated per week.png")
        # close and dont show the plot
        plt.close()

    sum_axis = number_of_pv
    sum_pv_energy_power_rel = sum(plantEnergySum) / sum(plantPowerTotal)
    sum_pv_energy_area_related = sum(plantEnergySum) / sum(plantAreaTotal)
    sum_pv_energy = sum(plantEnergySum)
    color = color_map[df_energyProfileSummary.columns[sum_axis]]
    create_hourly_plot_summed(df_energyProfileSummary, sum_axis, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, max_value=max_value_hourly)
    plt.savefig(f"{resultPath}/Summiertes PV-Leistungsprofil aller PV-Anlagen.png")

    create_aggregated_plot_summed(df_energyProfileSummary, sum_axis, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'M', months, rot=-45)
    plt.savefig(f"{resultPath}/Summiertes PV-Leistungsprofil aller PV-Anlagen aggregated per month.png")
    # close and dont show the plot
    plt.close()

    create_aggregated_plot_summed(df_energyProfileSummary, sum_axis, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'W', weeks, rot=-45)
    plt.savefig(f"{resultPath}/Summiertes PV-Leistungsprofil aller PV-Anlagen aggregated per week.png")
    # close and dont show the plot
    plt.close()


    # create comparison plots
    create_hourly_compare_plot(df_energyProfileSummary, color_map)
    plt.savefig(f"{resultPath}/Vergleich PV-Energieprofil aller PV-Anlagen.png")

    create_aggregated_compare_plot(df_energyProfileSummary, color_map, 'M', months, rot=-45)
    plt.savefig(f"{resultPath}/Vergleich PV-Energieprofil aller PV-Anlagen aggregated per month.png")
    # close and dont show the plot
    plt.close()

    create_aggregated_compare_plot(df_energyProfileSummary, color_map, 'W', weeks, rot=-45)
    plt.savefig(f"{resultPath}/Vergleich PV-Energieprofil aller PV-Anlagen aggregated per week.png")
    # close and dont show the plot
    plt.close()

    # show all non-closed plots
    if showPlot:
        plt.show()

    # close all remaining plots
    plt.close('all')
    

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
                city = (address.get('city') + ' - ' + address.get('suburb'))
            elif isinstance(address.get('city_district'), str):
                city = (address.get('city') + ' - ' + address.get('city_district'))
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
            logging().info('City: ' + address.get('postcode') + ' ' + city)
        else:
            logging().info('City: ' + city)
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
        weatherData = requestTryData(latitude, longitude)  # modified .dat file crawled from DWD and saved locally
    inputJson["weatherData"] = weatherData.serialize()
    sodeleInput = sodele.SodeleInput.deserialize(inputJson)

    print_location_information(weatherData.latitude, weatherData.longitude)

    result, plantInfo = simulatePVPlants(sodeleInput)

    energyProfiles = []
    energyAreaProfiles = []

    for pvResult in result["PhotovoltaicResults"]["PhotovoltaicPlants"]:
        energyProfiles.append(pvResult["EnergyProfile"])
        energyAreaProfiles.append(pvResult["EnergyAreaProfile"])

    energyProfiles.append(result["PhotovoltaicResults"]["SummaryOfAllPlants"]["EnergyProfile"])
    energyAreaProfiles.append(result["PhotovoltaicResults"]["SummaryOfAllPlants"]["EnergyAreaProfile"])

    plantEnergyKWPSum = []
    plantEnergySum = []
    plantAreaTotal = []
    plantPowerTotal = []
    for plant in plantInfo:
        plantEnergyKWPSum.append(plant.energyKWPSum)
        plantEnergySum.append(plant.energyProfileSum)
        plantAreaTotal.append(plant.surfaceArea)
        plantPowerTotal.append(plant.systemKWP)

    # remove the .json from the filePath
    basePath = filePath[:-5]
    resultPath = basePath + "_result"
    # create folder for the results
    if not os.path.exists(resultPath):
        os.makedirs(resultPath)

    # save the result
    with open(resultPath + "/result.json", "w") as f:
        json.dump(result, f, indent=4)

    visualizePVPlants(energyProfiles, energyAreaProfiles, resultPath, sodeleInput.showPlots, plantEnergyKWPSum, plantAreaTotal, plantPowerTotal, plantEnergySum)


if __name__ == "__main__":
    # get the path to the input json from argv
    pathToInputJson = sys.argv[1]
    #pathToInputJson = "./docs/testInput.json"

    if not os.path.exists(pathToInputJson):
        raise FileNotFoundError(f"Could not find the input json at {pathToInputJson}")
    with open(pathToInputJson, "r") as f:
        inputJson = json.load(f)
    main(inputJson, filePath=pathToInputJson)
