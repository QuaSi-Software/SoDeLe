import tempfile

import pandas as pd
import pvlib
# [MIT Licence] transformation of coordinates for DWD data
import pyproj
import re

from sodele import WeatherData, WeatherEntry


def with_tempfile(func):
    """
    Decorator to create a temporary file for the given function.
    """

    def wrapper(*args, **kwargs):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(args[0])
            temp_file.flush()
            result = func(temp_file.name, *args[1:], **kwargs)
            return result

    return wrapper


@with_tempfile
def read_in_dat_file(dat_file_path: bytes) -> WeatherData:
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
        dat_file_raw = open(str(dat_file_path), 'r')
    except Exception as e:
        raise ValueError(f"Could not read in the .dat weather data file {dat_file_path}. The following error occured: " + str(e))


    # read metadata from header
    metadata = dict()
    current_line = 0
    last_line = ""
    column_names = []
    # can be any letterCombination but not white space
    column_regex = r"[a-zA-Z]+"
    column_regex = re.compile(column_regex)

    int_regex = r"\d+"
    int_regex = re.compile(int_regex)

    meta_keys = {
        "Rechtswert": {
            "target": "Rechtswert",
            "converter": lambda x: int(int_regex.findall(x)[0])
        },
        "Hochwert": {
            "target": "Hochwert",
            "converter": lambda x: int(int_regex.findall(x)[0])
        },
        "Hoehenlage": {
            "target": "altitude",
            "converter": lambda x: int(int_regex.findall(x)[0])
        },
        "Art des TRY": {
            "target": "kind",
            "converter": lambda x: str(x.strip())
        },
    }

    for line in dat_file_raw:
        # Break loop of reading the header if data block has startet.
        # Begin of data has to start with "***"" with coloum names in the line bevore
        if line.startswith("***"):
            try:
                column_name_row = last_line
                # find all matches of the regex in the line
                column_matches = column_regex.findall(column_name_row)
                # create a list of column names
                column_names = [match for match in column_matches]
            except Exception as e:
                raise ValueError(f"Could not read in the column names of .dat weather data file {dat_file_path}. The following error occured: " + str(e))
            break

        # check if the line is needed for metadata
        for meta_key, meta_key_info in meta_keys.items():
            if line.startswith(meta_key):
                row = line.split(":")
                data = row[1]
                try:
                    validated_data = meta_key_info["converter"](data)
                except Exception as e:
                    raise ValueError(f"Could not read in the metadata of .dat weather data file {dat_file_path}. The following error occured: " + str(e))
                metadata[meta_key_info["target"]] = validated_data

        current_line += 1
        last_line = line

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
        dat_data = pd.read_table(dat_file_raw, header=None, names=column_names, sep=r"\s+")
    except Exception as e:
        raise ValueError(f"Could not read the datapoints in the .dat weather data file {dat_file_path}. The following error occured: " + str(e))

    if dat_data.shape[0] != 8760:
        raise ValueError(f"Could not read in the .dat weather data file {dat_file_path}. " + str(
            dat_data.shape[0]) + " datapoints has been read in instead of 8760. Checke the .dat file and make sure, that the datapoints begin with ""***""!")

    # create index that supplies correct date and time zone information
    # using 2015 as reference year and starting at 00:00 --> set to 00:30 for correct results!!! But in order to get constistency with epw, 00:00 is chosen.
    dat_range = pd.date_range(start=f'{2015}-01-01 00:00:00', end=f'{2015}-12-31 23:00:00', freq='h', tz=int(metadata['TZ'] * 60 * 60))
    dat_data.index = pd.DatetimeIndex(dat_range)  # tz in seconds with respect to GMT

    # adjust units
    dat_data["p"] = dat_data["p"] * 100  # convert hPa to Pa to be consistent with EPW

    df_weatherData = pd.DataFrame()
    df_weatherData.index = dat_data.index
    df_weatherData["date"] = dat_range
    df_weatherData["temp_air"] = dat_data["t"]
    df_weatherData["relative_humidity"] = dat_data["RF"]
    df_weatherData["wind_speed"] = dat_data["WG"]
    df_weatherData["atmospheric_pressure"] = dat_data["p"]
    df_weatherData["dhi"] = dat_data["D"]  # diffus horizontal radiation, naming as in pvlib/EPW
    df_weatherData["ghi"] = df_weatherData["dhi"] + dat_data["B"]  # global horizontal radiation = direct and diffuse horizontal radiation
    # all cols to df_weatherData
    for col in column_names:
        df_weatherData[col] = dat_data[col]

    return WeatherData(
        altitude=metadata.get('altitude', 0),
        latitude=metadata['latitude'],
        longitude=metadata['longitude'],
        kind=metadata.get('kind', 'unknown'),
        years=metadata.get('years', 2015),
        tz=metadata.get('TZ', 1),
        adjustTimestamp=metadata.get('adjustTimestamp', True),
        recalculateDNI=metadata.get('recalculateDNI', True),
        timeshiftInMinutes=metadata.get('timeshiftInMinutes', 30),
        weatherData=WeatherEntry(
            timeStamps=df_weatherData["date"].tolist(),
            month=df_weatherData["date"].dt.month.tolist(),
            day=df_weatherData["date"].dt.day.tolist(),
            hour=df_weatherData["date"].dt.hour.tolist(),
            temp_air=df_weatherData["temp_air"].tolist(),
            atmospheric_pressure=df_weatherData["atmospheric_pressure"].tolist(),
            wind_direction=df_weatherData["WR"].tolist(),
            wind_speed=df_weatherData["wind_speed"].tolist(),
            sky_cover=df_weatherData["N"].tolist(),
            precipitable_water=df_weatherData["x"].tolist(),
            relative_humidity=df_weatherData["relative_humidity"].tolist(),
            dni=df_weatherData["B"].tolist(),
            ghi=df_weatherData["ghi"].tolist(),
            dhi=df_weatherData["dhi"].tolist()
        )
    )


@with_tempfile
def read_in_epw_file(epwFile: bytes) -> WeatherData:
    df_weather, metadata = pvlib.iotools.read_epw(epwFile)
    year = df_weather["year"]
    # convert to dt and get month
    month = df_weather["month"]
    day = df_weather["day"]
    hour = df_weather["hour"]
    df_weather["timeStamps"] = pd.to_datetime(dict(year=year, month=month, day=day, hour=hour))

    return WeatherData(
        altitude=metadata["altitude"],
        kind="epw",
        years=1,
        latitude=metadata["latitude"],
        longitude=metadata["longitude"],
        tz=metadata["TZ"],
        adjustTimestamp=True,
        recalculateDNI=True,
        timeshiftInMinutes=30,
        weatherData=WeatherEntry(
            timeStamps=df_weather["timeStamps"].tolist(),
            month=df_weather["timeStamps"].dt.month.tolist(),
            day=df_weather["timeStamps"].dt.day.tolist(),
            hour=df_weather["timeStamps"].dt.hour.tolist(),
            temp_air=df_weather["temp_air"].tolist(),
            atmospheric_pressure=df_weather["atmospheric_pressure"].tolist(),
            wind_direction=df_weather["wind_direction"].tolist(),
            wind_speed=df_weather["wind_speed"].tolist(),
            sky_cover=df_weather["total_sky_cover"].tolist(),
            precipitable_water=df_weather["precipitable_water"].tolist(),
            relative_humidity=df_weather["relative_humidity"].tolist(),
            dni=df_weather["dni"].tolist(),
            ghi=df_weather["ghi"].tolist(),
            dhi=df_weather["dhi"].tolist()
        ))


if __name__ == "__main__":
    # Test the functions
    dat_file_path_2015 = "./docs/TRY2015_487959087814_Jahr.dat"
    dat_file_path_2045 = "./docs/TRY2045_487050089946_Jahr.dat"
    epw_file_path = "./docs/DEU_SN_Leipzig.Holzhausen.104710_TMYx.epw"

    with open(dat_file_path_2015, "rb") as f:
        dat_file_raw = f.read()
        weather_data_data_2015 = read_in_dat_file(dat_file_raw)

    with open(dat_file_path_2045, "rb") as f:
        dat_file_raw = f.read()
        weather_data_data_2045 = read_in_dat_file(dat_file_raw)

    with open(epw_file_path, "rb") as f:
        epw_file_raw = f.read()
        weather_data_epw = read_in_epw_file(epw_file_raw)


