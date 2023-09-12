import numpy as np
import pandas as pd
import pvlib

import sodele.Helper.optionsConcstructor as optConstruct
from sodele.Config import logging


class WeatherData:
    """
    This class is used to store weather data.

    :param rechtswert:      the rechtswert
    :type rechtswert:       int
    :param hochwert:        the hochwert
    :type hochwert:         int
    :param altitude:        the altitude
    :type altitude:         float
    :param kind:            the kind (e.g. 'mittleres Jahr')
    :type kind:             str
    :param years:           the years as a range like 2010-2019
    :type years:            int
    :param latitude:        the latitude
    :type latitude:         float
    :param longitude:       the longitude
    :type longitude:        float
    :param tz:              the timezone
    :type tz:               int
    :param adjustTimestamp: if the timestamp should be adjusted
    :type adjustTimestamp:  bool
    :param recalculateDNI:  if the DNI should be recalculated
    :type recalculateDNI:   bool
    :param timeshiftInMinutes: the timeshift in minutes
    :type timeshiftInMinutes:  int
    :param df_weatherData: the weather data as a pandas dataframe
    :type df_weatherData:  pandas.DataFrame
    """

    def __init__(self,
                 rechtswert: int, hochwert: int, altitude: float,
                 kind: str, years: int,
                 latitude: float, longitude: float,
                 tz: int,
                 adjustTimestamp: bool, recalculateDNI: bool, timeshiftInMinutes: int,
                 df_weatherData: pd.DataFrame):
        self.shouldAdjustTimestamp = adjustTimestamp
        self.shouldRecalculateDNI = recalculateDNI
        self.timeshiftInMinutes = timeshiftInMinutes
        self.rechtwert = rechtswert
        self.hochwert = hochwert
        self.altitude = altitude
        self.kind = kind
        self.years = years
        self.latitude = latitude
        self.longitude = longitude
        self.tz = tz

        self.df_weatherData = df_weatherData

    @staticmethod
    def deserialize(json):
        """
        Deserializes the weather data.

        :param json:
        :type json: dict
        :return:
        """
        rechtswert = json["rechtswert"]
        hochwert = json["hochwert"]
        altitude = json["altitude"]
        kind = json["kind"]
        years = json["years"]
        latitude = json["latitude"]
        longitude = json["longitude"]
        tz = json["TZ"]
        adjustTimestamp = json["adjustTimestamp"]
        recalculateDNI = json["recalculateDNI"]
        timeshiftInMinutes = json["timeshiftInMinutes"]

        df_weatherData = pd.DataFrame.from_dict(json["weatherData"])
        # set the column "timeStamps" as index
        df_weatherData["timeStamps"] = pd.to_datetime(df_weatherData["timeStamps"])
        df_weatherData.set_index("timeStamps", inplace=True)
        return WeatherData(rechtswert, hochwert, altitude,
                           kind, years,
                           latitude, longitude, tz,
                           adjustTimestamp, recalculateDNI, timeshiftInMinutes,
                           df_weatherData)

    def adjustTimeStamp(self):
        """
        Function to shift the time stamp of the weather dataframe by {timeshift} minutes
        The time period, freqency and the time zone will not be affected!
        """

        newTimeIndex = self.df_weatherData.index + pd.Timedelta(minutes=self.timeshiftInMinutes)
        newStartTime = newTimeIndex[0]

        # set the new time index
        self.df_weatherData.index = newTimeIndex

        logging().info(f"Time stamp of weather data was adjusted by {self.timeshiftInMinutes} minutes. New start time: {newStartTime}")

    def recalculateDNI(self):
        """
        Function to recalculate the DNI of the weather dataframe
        """

        # calculate solar height using pvlib and default method nrel_numpy [deg]
        # see pvlib.solarposition.get_solarposition for further information
        solarPosition = pvlib.solarposition.get_solarposition(self.df_weatherData.index,
                                                              self.latitude, self.longitude, altitude=self.altitude,
                                                              pressure=self.df_weatherData["atmospheric_pressure"],
                                                              method='nrel_numpy')
        # calculate direct normal iradiation using pvlib; fill nan values with zero nad replace -0.0 values with 0.0
        dni = pvlib.irradiance.dni(self.df_weatherData["ghi"], self.df_weatherData["dhi"], solarPosition["zenith"])
        dni = dni.fillna(0.0)
        dni = np.nan_to_num(dni, nan=0.0)
        dni[dni == -0.0] = 0.0

        # replace the DNI column with the recalculated values
        self.df_weatherData["dni"] = dni

    def serialize(self):
        """
        Serializes the weather data.

        :return:
        """
        weatherData = self.df_weatherData.copy()
        weatherData.reset_index(inplace=True)
        weatherDataResult = {}
        for column in weatherData.columns:
            weatherDataResult[column] = weatherData[column].tolist()

        return {
            "rechtswert": self.rechtwert,
            "hochwert": self.hochwert,
            "altitude": self.altitude,
            "kind": self.kind,
            "years": self.years,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "TZ": self.tz,
            "adjustTimestamp": self.adjustTimeStamp,
            "recalculateDNI": self.recalculateDNI,
            "timeshiftInMinutes": self.timeshiftInMinutes,
            "weatherData": weatherDataResult
        }

    @staticmethod
    def options() -> dict:
        """
        Returns the options for the weather data.

        :return:
        """
        return {
            **optConstruct.getInteger("rechtswert", "Rechtswert", required=True),
            **optConstruct.getInteger("hochwert", "Hochwert", required=True),
            **optConstruct.getFloat("altitude", "Altitude", required=True),
            **optConstruct.getString("kind", "Kind Of Reference Year", required=True),
            **optConstruct.getString("years", "Years Span", required=True),
            **optConstruct.getFloat("latitude", "Latitude", required=True),
            **optConstruct.getFloat("longitude", "Longitude", required=True),
            **optConstruct.getInteger("tz", "Timezone", required=True),
            **optConstruct.getBoolean("adjustTimestamp", "Adjust Timestamp", required=True),
            **optConstruct.getBoolean("recalculateDNI", "Recalculate DNI", required=True),
            **optConstruct.getInteger("timeshiftInMinutes", "Timeshift In Minutes", required=True),
            "weatherData": optConstruct.getList(["timeStamps", "month", "day", "hour", "temp_air",
                                                 "atmospheric_pressure", "wind_direction", "wind_speed",
                                                 "sky_cover", "precipitable_water", "relative_humidity",
                                                 "athmospheric_heat_irr", "dhi", "ghi", "dni"])

        }
