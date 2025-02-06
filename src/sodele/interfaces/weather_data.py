import pandas as pd
import pvlib
import numpy as np
from pandas import Timestamp

from sodele.interfaces.base import Base
from pydantic import Field
from typing import Any, cast


class WeatherEntry(Base):
    timeStamps: list[Timestamp] = Field(..., description="Time Stamps")
    month: list[int] = Field(..., description="Month")
    day: list[int] = Field(..., description="Day")
    hour: list[int] = Field(..., description="Hour")
    temp_air: list[float] = Field(..., description="Temperature Air")
    atmospheric_pressure: list[float] = Field(..., description="Atmospheric Pressure")
    wind_direction: list[float] = Field(..., description="Wind Direction")
    wind_speed: list[float] = Field(..., description="Wind Speed")
    sky_cover: list[float] = Field(..., description="Sky Cover")
    precipitable_water: list[float] = Field(..., description="Precipitable Water")
    relative_humidity: list[float] = Field(..., description="Relative Humidity")
    dni: list[float] = Field(..., description="Direct Normal Irradiance")
    ghi: list[float] = Field(..., description="Global Horizontal Irradiance")
    dhi: list[float] = Field(..., description="Diffuse Horizontal Irradiance")

    class Config:
        arbitrary_types_allowed = True


class WeatherData(Base):
    altitude: float = Field(..., description="Altitude")
    kind: str = Field(..., description="Kind Of Reference Year")
    years: int = Field(..., description="Years Span")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    tz: int = Field(..., description="Timezone")
    adjustTimestamp: bool = Field(..., description="Adjust Timestamp")
    recalculateDNI: bool = Field(..., description="Recalculate DNI")
    timeshiftInMinutes: int = Field(..., description="Timeshift In Minutes")
    weatherData: WeatherEntry = Field(..., description="Weather Data")

    _df_weatherData: pd.DataFrame | None = None

    @property
    def df_weatherData(self) -> pd.DataFrame | None:
        return self._df_weatherData

    def model_post_init(self, __context: Any) -> None:
        self.generate_df()

    def generate_df(self) -> None:
        df = pd.DataFrame.from_dict(self.weatherData.model_dump())
        pd_time_series = pd.to_datetime(df["timeStamps"])
        df.index = pd_time_series
        self._df_weatherData = df

    def adjust_time_stamp(self) -> None:
        """
        Function to shift the time stamp of the weather dataframe by {timeshift} minutes
        The time period, freqency and the time zone will not be affected!
        """
        df_weatherData: pd.DataFrame | None = self._df_weatherData
        if df_weatherData is None:
            return

        new_time_index = df_weatherData.index + pd.Timedelta(minutes=self.timeshiftInMinutes)
        new_start_time = new_time_index[0]

        # update the time stamps in the weather data
        self.weatherData.timeStamps = new_time_index.to_list()
        self.generate_df()

    def recalculate_dni(self) -> None:
        """
        Function to recalculate the DNI of the weather dataframe
        """
        if self._df_weatherData is None:
            return
        df_weatherData: pd.DataFrame = self._df_weatherData
        # calculate solar height using pvlib and default method nrel_numpy [deg]
        solar_position = pvlib.solarposition.get_solarposition(
            cast(pd.DatetimeIndex, df_weatherData.index),
            self.latitude,
            self.longitude,
            altitude=self.altitude,
            pressure=self.df_weatherData["atmospheric_pressure"],
            method="nrel_numpy",
        )
        # calculate direct normal irradiation using pvlib; fill nan values with zero nad replace -0.0 values with 0.0
        dni = pvlib.irradiance.dni(
            self.df_weatherData["ghi"],
            self.df_weatherData["dhi"],
            solar_position["zenith"],
        )
        dni = dni.fillna(0.0)
        dni = np.nan_to_num(dni, nan=0.0)
        dni[dni == -0.0] = 0.0

        # replace the DNI column with the recalculated values
        self.weatherData.dni = list(dni)
        self.generate_df()
