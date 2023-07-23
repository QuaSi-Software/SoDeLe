import uuid

from sodele.Helper.dictor import dictor
import sodele.Helper.optionsConcstructor as optConstruct


class PhotovoltaicPlant:
    """
    PhotovoltaicPlant class

    :param uid:                     The unique identifier of the photovoltaic plant.
    :type uid:                      uuid.UUID
    :param surfaceAzimuth:          The surface azimuth of the photovoltaic plant.
    :type surfaceAzimuth:           float (0° = North, 90° = East, 180° = South, 270° = West)
    :param surfaceTilt:             The surface tilt of the photovoltaic plant. (0° = horizontal, 90° = vertical)
    :type surfaceTilt:              float
    :param modulesPerString:        The number of modules per string.
    :type modulesPerString:         float
    :param stringsPerInverter:      The number of strings per inverter.
    :type stringsPerInverter:       int
    :param numberOfInverters:       The number of inverters.
    :type numberOfInverters:        int
    :param albedo:                  The albedo of the surface:
                                        0.2 - Default
                                        0.2 - Grass
                                        0.3 - Concrete
                                        0.33 - Red Brick
                                        0.35 - Steel
                                        0.4 - Sand
                                        0.65 - old Snow
                                        0.74 - copper
                                        0.85 - aluminium
    :type albedo:                   float
    :param moduleInstallation:      The module installation type:
                                        1 - Good back ventilation, Glas back
                                        2 - Good back ventilation, Polymer back
                                        3 - closed back, Glas back
                                        4 - isolated back, Polymer back
    :type moduleInstallation:       int

    :param energyProfile:           (result) The energy profile of the photovoltaic plant.
    :type energyProfile:            list[float] | None
    :param surfaceArea:             (result) The surface area of the photovoltaic plant.
    :type surfaceArea:              float | None
    :param systemKWP:               (result) The system KWP of the photovoltaic plant.
    :type systemKWP:                float | None

    :param energyProfileArea:       (result) The energy profile area of the photovoltaic plant.
    :type energyProfileArea:        list[float] | None
    :param energyProfileSum:        (result) The energy profile sum of the photovoltaic plant.
    :type energyProfileSum:         float | None
    :param energyProfileAreaSum:    (result) The energy profile area sum of the photovoltaic plant.
    :type energyProfileAreaSum:     float | None
    """

    def __init__(self,
                 uid,
                 surfaceAzimuth: float, surfaceTilt: float,
                 modulesPerString: float, stringsPerInverter: int, numberOfInverters: int,
                 albedo: float, moduleInstallation: int):
        self.uid = uid
        self.surfaceAzimuth = surfaceAzimuth
        self.surfaceTilt = surfaceTilt
        self.modulesPerString = modulesPerString
        self.stringsPerInverter = stringsPerInverter
        self.numberOfInverters = numberOfInverters
        self.albedo = albedo
        self.moduleInstallation = moduleInstallation
        self.energyProfile = None
        self.surfaceArea = None
        self.systemKWP = None

    @staticmethod
    def deserialize(json: dict):
        """
        Deserializes the PhotovoltaicPlant.

        :param json:
        :type json: dict
        :return: PhotovoltaicPlant
        """
        uid = dictor(json, "uid", uuid.uuid4())
        surfaceAzimuth = dictor(json, "surfaceAzimuth", 0)
        surfaceTilt = dictor(json, "surfaceTilt", 0)
        modulesPerString = dictor(json, "modulesPerString", 0)
        stringsPerInverter = dictor(json, "stringsPerInverter", 0)
        numberOfInverters = dictor(json, "numberOfInverters", 0)
        albedo = dictor(json, "albedo", 0.2)
        moduleInstallation = dictor(json, "moduleInstallation", 1)
        return PhotovoltaicPlant(uid,
                                 surfaceAzimuth, surfaceTilt,
                                 modulesPerString, stringsPerInverter, numberOfInverters,
                                 albedo, moduleInstallation)

    def serialize(self) -> dict:
        """
        Serializes the PhotovoltaicPlant.

        :return: dict
        """
        return {
            "surfaceAzimuth": self.surfaceAzimuth,
            "surfaceTilt": self.surfaceTilt,
            "modulesPerString": self.modulesPerString,
            "stringsPerInverter": self.stringsPerInverter,
            "numberOfInverters": self.numberOfInverters,
            "albedo": self.albedo,
            "moduleInstallation": self.moduleInstallation
        }

    @staticmethod
    def options() -> dict:
        """
        Returns the options for the PhotovoltaicPlant.

        :return:
        """
        return {
            **optConstruct.getFloat("surfaceAzimuth", "Surface azimuth"),
            **optConstruct.getFloat("surfaceTilt", "Surface tilt"),
            **optConstruct.getFloat("modulesPerString", "Modules per string"),
            **optConstruct.getInteger("stringsPerInverter", "Strings per inverter"),
            **optConstruct.getInteger("numberOfInverters", "Number of inverters"),
            **optConstruct.getFloat("albedo", "Albedo", default=0.2),
            **optConstruct.getInteger("moduleInstallation", "Module installation", default=1)
        }

    def calculateProfileMetrics(self):
        """
        Calculates the profile metrics.

        Speaking of:
            - self.energyProfileArea
            - self.energyProfileSum
            - self.energyProfileAreaSum
        :return:
        """

        self.energyProfileSum = sum(self.energyProfile)
        self.energyProfileArea = [energyProfileValue / self.surfaceArea for energyProfileValue in self.energyProfile]
        self.energyProfileAreaSum = self.energyProfileSum / self.surfaceArea
        self.energyKWPSum = self.energyProfileSum / self.systemKWP

