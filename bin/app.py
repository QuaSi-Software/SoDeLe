import json
import os

import logging

import click
import dotenv
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
# [MIT Licence] get location from coordinates
from geopy.geocoders import Nominatim

import sodele
from dbi.dbi_connect_get_token import get_token
from dbi.dbi_fetch_weather_data import fetch_weather_data
from sodele import simulate_pv_plants, WeatherData
from sodele.core.weather_data_reader import read_in_dat_file, read_in_epw_file

# load the .env file
dotenv.load_dotenv()

logger = logging.getLogger("SoDeLe")


def request_try_data(latitude: float, longitude: float) -> WeatherData:
    """
    Requests in the try data that has been pre-download from "DWD Klimaberatungsmodule".

    :param latitude:    The latitude.
    :param longitude:   The longitude.
    :return:    The try data.
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
    )

    logger.info(f"The weather data has been loaded from predownloaded DWD TRY files for Lat: '{latitude}' and Long: '{longitude}' with {df_weatherData.shape[0]} datapoints successfully.")

    return weatherData


def read_in_weather_data_file(weatherDataFile):
    if weatherDataFile.endswith(".dat"):
        with open(weatherDataFile, "rb") as f:
            lines = f.read()
            return read_in_dat_file(lines)
    elif weatherDataFile.endswith(".epw"):
        with open(weatherDataFile, "rb") as f:
            lines = f.read()
            return read_in_epw_file(lines)
    else:
        raise ValueError(f"Could not read in the weather data file {weatherDataFile}.")

def visualize_pv_plants(energyProfiles, energyAreaProfiles, resultPath, showPlot, plantEnergyKWPSum, plantAreaTotal, plantPowerTotal, plantEnergySum):
    fignum = 1

    def create_hourly_plot(df_data, col_idx, color, sum_pv, sum_pv_power, sum_pv_area, max_value=None, with_text=True):
        nonlocal fignum
        # Create a barplot of the data
        plt.figure(fignum)
        fignum += 1
        sns.lineplot(data=df_data, x=df_data.index, y=df_data.columns[col_idx], color=color)
        plt.title(f"PV-Leistungsprofil fuer PV-Anlage {col_idx + 1}")
        plt.xlabel('Zeitschritte im Jahr (entspricht Zeitschrittweite des Wetterdatensatzes)')
        plt.ylabel('el. Leistung gemittelt ueber Zeitschritt [kW]')

        if max_value is None:
            max_value = df_data.iloc[:, col_idx].max()

        # set the y axis range from 0-1.1 times the max value
        max_value = max(max_value, 1)
        plt.ylim(0, max_value)
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
        plt.title(f"PV-Leistungsprofil fuer PV-Anlage {col_idx + 1}")
        plt.xlabel('Zeitschritte im Jahr')
        plt.ylabel('el. Leistung gemittelt ueber Zeitschritt [kW]')

        if max_value is None:
            max_value = df_data.iloc[:, col_idx].max()

        # set the y axis range from 0-1.1 times the max value
        max_value = max(max_value, 1)
        plt.ylim(0, max_value)
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
        max_value = max(1, max_value * 1.1)
        plt.ylim(0, max_value)

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
        plt.ylabel('el. Leistung gemittelt ueber Zeitschritt [kW]')

        max_value = df_data['value'].max()

        # set the y axis range from 0-1.1 times the max value
        max_val = max(1, max_value * 1.1)
        plt.ylim(0, max_val)

        # set the xticks to the labels
        plt.xticks(range(len(labels)), labels)
        # rotate the labels
        plt.xticks(rotation=rot)

    # create individual plots for each plant
    numberOfPlants = len(energyProfiles) - 1
    columns = [f"PV_Plant_{i+1}" for i in range(numberOfPlants)] + ["Summary of all Plants"]

    df_energyProfileSummary = pd.DataFrame()
    df_areaProfileSummary = pd.DataFrame()
    df_energyProfileSummary.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='h'))  # tz in seconds with respect to GMT
    df_areaProfileSummary.index = pd.DatetimeIndex(pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='h'))  # tz in seconds with respect to GMT
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
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    weeks = [f"KW {i}" for i in range(1, 54)]

    for pv_plant_idx in range(number_of_pv):
        sum_pv_energy_power_rel = plantEnergyKWPSum[pv_plant_idx]
        sum_pv_energy_area_related = df_areaProfileSummary.iloc[:, pv_plant_idx].sum()
        sum_pv_energy = plantEnergySum[pv_plant_idx]
        color = color_map[df_energyProfileSummary.columns[pv_plant_idx]]
        create_hourly_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil fuer PV-Anlage {pv_plant_idx + 1}.png")

        create_aggregated_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'ME', months, rot=-45)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil fuer PV-Anlage {pv_plant_idx + 1} aggregated per month.png")
        # close and dont show the plot
        plt.close()

        create_aggregated_plot(df_energyProfileSummary, pv_plant_idx, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'W', weeks, rot=-45)
        plt.savefig(f"{resultPath}/PV-Leistungsprofil fuer PV-Anlage {pv_plant_idx + 1} aggregated per week.png")
        # close and dont show the plot
        plt.close()

    sum_axis = number_of_pv
    sum_pv_energy_power_rel = sum(plantEnergySum) / sum(plantPowerTotal)
    sum_pv_energy_area_related = sum(plantEnergySum) / sum(plantAreaTotal)
    sum_pv_energy = sum(plantEnergySum)
    color = color_map[df_energyProfileSummary.columns[sum_axis]]
    create_hourly_plot_summed(df_energyProfileSummary, sum_axis, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related)
    plt.savefig(f"{resultPath}/Summiertes PV-Leistungsprofil aller PV-Anlagen.png")

    create_aggregated_plot_summed(df_energyProfileSummary, sum_axis, color, sum_pv_energy, sum_pv_energy_power_rel, sum_pv_energy_area_related, 'ME', months, rot=-45)
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

    create_aggregated_compare_plot(df_energyProfileSummary, color_map, 'ME', months, rot=-45)
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
    logger.info("-----")
    logger.info("The coordinates given in the provided .dat-file or as input value are:")
    logger.info("Latitude: " + str(latitude))
    logger.info("Longitude: " + str(longitude))

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
            logger.info('City: ' + address.get('postcode') + ' ' + city)
        else:
            logger.info('City: ' + city)
        if isinstance(address.get('state'), str):
            logger.info('State: ' + address.get('state'))
        if isinstance(address.get('country'), str):
            logger.info('Country: ' + address.get('country'))
    except Exception as e:
        logger.info("Detailed information on the location could not be received from the online server...")
        logger.info('Error message: ' + str(e))

    logger.info("-----")

    return


@click.command("simulatePv")
@click.option('--input_json', '-i', help='The path to the input json file.', required=True)
def simulate_pv(input_json):
    filePath = os.path.abspath(input_json)
    if not os.path.exists(input_json):
        raise FileNotFoundError(f"Could not find the input json at {input_json}")

    with open(input_json, "r") as f:
        inputJsonDict = json.load(f)

    latitude = inputJsonDict.get("weatherData", {}).get("latitude", None)
    longitude = inputJsonDict.get("weatherData", {}).get("longitude", None)
    weatherDataFile = inputJsonDict.get("weatherData", {}).get("weatherDataFile", None)
    if weatherDataFile is not None:
        weatherData = read_in_weather_data_file(weatherDataFile)  # .dat or .epw file externally given by absolute or relative path
    else:
        weatherData = request_try_data(latitude, longitude)  # modified .dat file crawled from DWD and saved locally
    inputJsonDict["weatherData"] = weatherData.model_dump()
    sodeleInput = sodele.SodeleInput.model_validate(inputJsonDict)

    print_location_information(weatherData.latitude, weatherData.longitude)

    result_obj, plantInfo = simulate_pv_plants(sodeleInput)
    result = result_obj.model_dump()

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

    visualize_pv_plants(energyProfiles, energyAreaProfiles, resultPath, sodeleInput.showPlots, plantEnergyKWPSum, plantAreaTotal, plantPowerTotal, plantEnergySum)


@click.command("generatePVDatabase")
@click.option('--path', '-p', help='The path where to store the csv files', required=True)
def generate_pv_database(path):
    from sodele.core.generate_pv_database import generate_pv_lib_database
    generate_pv_lib_database(path)


@click.group()
def main():
    pass


main.add_command(simulate_pv)
main.add_command(generate_pv_database)