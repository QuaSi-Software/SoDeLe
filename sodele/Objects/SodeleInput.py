from sodele.Helper.dictor import dictor
from sodele.Objects.PhotovoltaicConfig import PhotovoltaicConfig
from sodele.Objects.PhotovoltaicPlant import PhotovoltaicPlant
from sodele.Objects.WeatherData import WeatherData


class SodeleInput:
    """
    SodeleInput class

    :param photovoltaicConfig:      The photovoltaic config.
    :type photovoltaicConfig:       PhotovoltaicConfig
    :param photovoltaicPlants:      The photovoltaic plants.
    :type photovoltaicPlants:       list[PhotovoltaicPlant]
    :param weatherData:             The weather data.
    :type weatherData:              WeatherData
    """

    def __init__(self,
                 photovoltaicConfig: PhotovoltaicConfig,
                 photovoltaicPlants: list[PhotovoltaicPlant],
                 showPlots: bool,
                 weatherData: WeatherData):
        self.photovoltaicConfig = photovoltaicConfig
        self.photovoltaicPlants = photovoltaicPlants
        self.showPlots = showPlots
        self.weatherData = weatherData

    @staticmethod
    def deserialize(json: dict):
        """
        Deserializes the sodele input.

        :param json:    The json.
        :type json:     dict
        :return:        The sodele input.
        :rtype:         SodeleInput
        """
        photovoltaicConfig = PhotovoltaicConfig.deserialize(json["PhotovoltaicConfig"])
        photovoltaicPlants = [PhotovoltaicPlant.deserialize(plant) for plant in json["PhotovoltaicPlants"]]
        weatherData = WeatherData.deserialize(json["weatherData"])
        showPlots = dictor(json, "showPlots", False)
        return SodeleInput(photovoltaicConfig, photovoltaicPlants, showPlots, weatherData)

    def serialize(self):
        """
        Serializes the sodele input.

        :return:    The json.
        :rtype:     dict
        """
        return {
            "PhotovoltaicConfig": self.photovoltaicConfig.serialize(),
            "PhotovoltaicPlants": [plant.serialize() for plant in self.photovoltaicPlants],
            "showPlots": self.showPlots,
            "weatherData": self.weatherData.serialize()
        }

    @staticmethod
    def options() -> dict:
        """
        Returns the options.

        :return:    The options.
        :rtype:     dict
        """
        return {
            "PhotovoltaicConfig": PhotovoltaicConfig.options(),
            "PhotovoltaicPlants": PhotovoltaicPlant.options(),
            "showPlots": "bool",
            "weatherData": WeatherData.options(),
        }
