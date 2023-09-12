import uuid

import pvlib

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

    :param lossesIrradiation:           The losses due to irradiation. in % (0-100)
    :type lossesIrradiation:            float
    :param lossesDCDatasheet:           The losses due to the datasheet. in % (0-100)
    :type lossesDCDatasheet:            float
    :param lossesDCCables:              The losses due to the DC cables. in % (0-100)
    :type lossesDCCables:               float

    :param modulesDatabaseType:         The type of the modules database.
    :type modulesDatabaseType:          int

    :param modulesDatabasePath:         The path to the modules database. Will be set automatically.
    :type modulesDatabasePath:          str
    :param inverterDatabasePath:        The path to the inverter database. Will be set automatically.
    :type inverterDatabasePath:         str

    :param useInverterDatabase:         Flag to indicate if the inverter database should be used.
    :type useInverterDatabase:          bool
    :param inverterName:                The name of the inverter.
    :type inverterName:                 str
    :param useStandByPowerInverter:     Flag to indicate if the stand by power of the inverter should be used. Otherwise a constant value of "inverterEta" is used.
    :type useStandByPowerInverter:      bool
    :param inverterEta:                 The efficiency of the inverter. as factor (0-1)
    :type inverterEta:                  float

    :param moduleName:                  The name of the module.
    :type moduleName:                   str
    """

    def __init__(self,
                 uid,
                 surfaceAzimuth: float, surfaceTilt: float,
                 modulesPerString: float, stringsPerInverter: int, numberOfInverters: int,
                 albedo: float, moduleInstallation: int,
                 moduleName: str,
                 lossesIrradiation: float, lossesDCDatasheet: float, lossesDCCables: float,
                 modulesDatabaseType: int,
                 useInverterDatabase: bool, inverterName: str, useStandByPowerInverter: bool, inverterEta: float):
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

        # configs
        self.moduleName = moduleName

        self.lossesIrradiation = lossesIrradiation
        self.lossesDCDatasheet = lossesDCDatasheet
        self.lossesDCCables = lossesDCCables

        self.modulesDatabaseType = modulesDatabaseType
        dataBases = self.getDatabasePaths(modulesDatabaseType)
        self.modulesDatabasePath = dataBases[0]
        self.invertersDatabasePath = dataBases[1]

        self.useInverterDatabase = useInverterDatabase
        self.inverterName = inverterName
        self.useStandByPowerInverter = useStandByPowerInverter
        self.inverterEta = inverterEta

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
        modulesDatabaseType = dictor(json, 'modulesDatabaseType', 2)

        try:
            moduleName = json['moduleName']

            lossesIrradiation = dictor(json, 'lossesIrradiation', 1.0)
            lossesDCDatasheet = dictor(json, 'lossesDCDatasheet', 2.0)
            lossesDCCables = dictor(json, 'lossesDCCables', 0.0)

            inverterName = json['inverterName']
            useInverterDatabase = dictor(json, 'useInverterDatabase', False)
            useStandByPowerInverter = dictor(json, 'useStandByPowerInverter', False)
            inverterEta = dictor(json, 'inverterEta', 0.92)
        except KeyError as e:
            raise KeyError(f"The key '{e}' is missing in the photovoltaic config.")

        return PhotovoltaicPlant(uid,
                                 surfaceAzimuth, surfaceTilt,
                                 modulesPerString, stringsPerInverter, numberOfInverters,
                                 albedo, moduleInstallation,
                                 moduleName,
                                 lossesIrradiation, lossesDCDatasheet, lossesDCCables,
                                 modulesDatabaseType,
                                 useInverterDatabase, inverterName, useStandByPowerInverter, inverterEta)

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
            "moduleInstallation": self.moduleInstallation,
            "moduleName": self.moduleName,
            "lossesIrradiation": self.lossesIrradiation,
            "lossesDCDatasheet": self.lossesDCDatasheet,
            "lossesDCCables": self.lossesDCCables,
            "modulesDatabaseType": self.modulesDatabaseType,
            "useInverterDatabase": self.useInverterDatabase,
            "inverterName": self.inverterName,
            "useStandByPowerInverter": self.useStandByPowerInverter,
            "inverterEta": self.inverterEta
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
            **optConstruct.getInteger("moduleInstallation", "Module installation", default=1),
            **optConstruct.getString("moduleName", "The Name of the PV Module", required=True, default=""),
            **optConstruct.getFloat("lossesIrradiation", "The losses due to irradiation. in % (0-100)", default=1.0),
            **optConstruct.getFloat("lossesDCDatasheet", "The losses due to the datasheet. in % (0-100)", default=2.0),
            **optConstruct.getFloat("lossesDCCables", "The losses due to the DC cables. in % (0-100)", default=0.0),
            **optConstruct.getInteger("modulesDatabaseType", "", default=1),
            **optConstruct.getBoolean("useInverterDatabase", "Flag to indicate if the inverter database should be used.", default=False),
            **optConstruct.getString("inverterName", "The name of the inverter.", required=True, default=""),
            **optConstruct.getBoolean("useStandByPowerInverter", "Flag to indicate if the stand by power of the inverter should be used. Otherwise a constant value of 'inverterEta' is used.", default=False),
            **optConstruct.getFloat("inverterEta", "The efficiency of the inverter. as factor (0-1)", default=0.92),
        }

    @staticmethod
    def getDatabasePaths(modulesDatabaseType: int):
        """
        Returns the database paths for the given modules database type.

        :param modulesDatabaseType:     The type of the modules database. (1 = CEC, 2 = Sandia)
        :type modulesDatabaseType:      int
        :return:                        (ModuleDatabase, InverterDatabase)
        """
        if modulesDatabaseType == 1:
            moduleDatabasePath = "./src/sodele/res/PV_Database/220225_Sandia_Modules.csv"
            inverterDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Inverters.csv"
            return moduleDatabasePath, inverterDatabasePath

        elif modulesDatabaseType == 2:
            moduleDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Modules.csv"
            moduleDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Inverters.csv"
            return moduleDatabasePath, moduleDatabasePath

        else:
            raise Exception(f"The given modules database type '{modulesDatabaseType}' is not supported.")

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

    def getModulesAndInverters(self):
        # set chosen module and inverter from database
        if self.modulesDatabaseType == 1:
            PV_modules = pvlib.pvsystem.retrieve_sam(name=None, path=self.modulesDatabasePath)
            PV_inverters = pvlib.pvsystem.retrieve_sam(name=None, path=self.invertersDatabasePath)

            current_module = PV_modules[self.moduleName]
            current_inverter = PV_inverters[self.inverterName]

            return current_module, current_inverter
        elif self.modulesDatabaseType == 2:
            PV_modules = pvlib.pvsystem.retrieve_sam("cecmod")
            PV_inverters = pvlib.pvsystem.retrieve_sam("cecinverter")

            current_module = PV_modules[self.moduleName]
            current_inverter = PV_inverters[self.inverterName]

            return current_module, current_inverter

