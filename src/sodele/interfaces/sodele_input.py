from sodele.interfaces.base import Base
from pydantic import Field
from sodele.interfaces.pv_specifics import PhotovoltaicPlant
from sodele.interfaces.weather_data import WeatherData
import uuid


class SodeleInput(Base):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the simulation.")
    keep_files: bool = Field(False, description="Whether to keep the files.")
    weatherData: WeatherData = Field(..., description="The weather data for the simulation.")
    photovoltaicPlants: list[PhotovoltaicPlant] = Field(..., description="The photovoltaic plants to simulate.")
    showPlots: bool = Field(False, description="Whether to show plots.")
