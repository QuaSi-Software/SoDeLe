from sodele.Helper.dictor import dictor
from sodele.Objects.PhotovoltaicPlant import PhotovoltaicPlant
from sodele.Objects.WeatherData import WeatherData


class SodeleInput:
    """
    SodeleInput class

    :param photovoltaicPlants:      The photovoltaic plants.
    :type photovoltaicPlants:       list[PhotovoltaicPlant]
    :param weatherData:             The weather data.
    :type weatherData:              WeatherData
    """

    def __init__(self,
                 photovoltaicPlants: list[PhotovoltaicPlant],
                 showPlots: bool,
                 weatherData: WeatherData):
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
        photovoltaicPlants = [PhotovoltaicPlant.deserialize(plant) for plant in json["PhotovoltaicPlants"]]
        weatherData = WeatherData.deserialize(json["weatherData"])
        showPlots = dictor(json, "showPlots", True)
        return SodeleInput(photovoltaicPlants, showPlots, weatherData)

    def serialize(self):
        """
        Serializes the sodele input.

        :return:    The json.
        :rtype:     dict
        """
        return {
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
            "PhotovoltaicPlants": PhotovoltaicPlant.options(),
            "showPlots": "bool",
            "weatherData": WeatherData.options(),
        }
