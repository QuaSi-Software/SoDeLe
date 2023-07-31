from sodele.Helper.dictor import dictor
import sodele.Helper.optionsConcstructor as optConstruct


class PhotovoltaicConfig:
    """
    PhotovoltaicConfig class

    :param modulesDatabaseType:         The type of the modules database.
    :type modulesDatabaseType:          int
    :param moduleName:                  The name of the module.
    :type moduleName:                   str

    :param lossesIrradiation:           The losses due to irradiation. in % (0-100)
    :type lossesIrradiation:            float
    :param lossesDCDatasheet:           The losses due to the datasheet. in % (0-100)
    :type lossesDCDatasheet:            float
    :param lossesDCCables:              The losses due to the DC cables. in % (0-100)
    :type lossesDCCables:               float

    :param useInverterDatabase:         Flag to indicate if the inverter database should be used.
    :type useInverterDatabase:          bool
    :param inverterName:                The name of the inverter.
    :type inverterName:                 str
    :param useStandByPowerInverter:     Flag to indicate if the stand by power of the inverter should be used. Otherwise a constant value of "inverterEta" is used.
    :type useStandByPowerInverter:      bool
    :param inverterEta:                 The efficiency of the inverter. as factor (0-1)
    :type inverterEta:                  float

    :param modulesDatabasePath:         The path to the modules database. Will be set automatically.
    :type modulesDatabasePath:          str
    :param inverterDatabasePath:        The path to the inverter database. Will be set automatically.
    :type inverterDatabasePath:         str
    """

    def __init__(self, modulesDatabaseType: int, moduleName: str,
                 lossesIrradiation: float, lossesDCDatasheet: float, lossesDCCables: float,
                 useInverterDatabase: bool, inverterName: str, useStandByPowerInverter: bool, inverterEta: float):
        self.modulesDatabaseType = modulesDatabaseType
        self.moduleName = moduleName

        self.lossesIrradiation = lossesIrradiation
        self.lossesDCDatasheet = lossesDCDatasheet
        self.lossesDCCables = lossesDCCables

        self.useInverterDatabase = useInverterDatabase
        self.inverterName = inverterName
        self.useStandByPowerInverter = useStandByPowerInverter
        self.inverterEta = inverterEta

        dataBases = self.getDatabasePaths(modulesDatabaseType)
        self.modulesDatabasePath = dataBases[0]
        self.invertersDatabasePath = dataBases[1]

    @staticmethod
    def deserialize(json: dict):
        """
        Deserializes the photovoltaic config.

        :param json:
        :type json: dict
        :return:
        """
        modulesDatabaseType = dictor(json, 'modulesDatabaseType', 1)

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

        return PhotovoltaicConfig(modulesDatabaseType, moduleName,
                                  lossesIrradiation, lossesDCDatasheet, lossesDCCables,
                                  useInverterDatabase, inverterName, useStandByPowerInverter, inverterEta)


    def serialize(self):
        """
        Serializes the photovoltaic config.

        :return: dict
        """
        return {
            "modulesDatabaseType": self.modulesDatabaseType,
            "moduleName": self.moduleName,
            "lossesIrradiation": self.lossesIrradiation,
            "lossesDCDatasheet": self.lossesDCDatasheet,
            "lossesDCCables": self.lossesDCCables,
            "useInverterDatabase": self.useInverterDatabase,
            "inverterName": self.inverterName,
            "useStandByPowerInverter": self.useStandByPowerInverter,
            "inverterEta": self.inverterEta
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
            moduleDatabasePath = "./sodele/res/PV_Database/220225_Sandia_Modules.csv"
            inverterDatabasePath = "./sodele/res/PV_Database/221115_CEC_Inverters.csv"
            return moduleDatabasePath, inverterDatabasePath

        elif modulesDatabaseType == 2:
            moduleDatabasePath = "./sodele/res/PV_Database/221115_CEC_Modules.csv"
            moduleDatabasePath = "./sodele/res/PV_Database/221115_CEC_Inverters.csv"
            return moduleDatabasePath, moduleDatabasePath

        else:
            raise Exception(f"The given modules database type '{modulesDatabaseType}' is not supported.")

    @staticmethod
    def options() -> dict:
        """
        Returns the options for the photovoltaic config.
        :return: dict
        """

        return {
            **optConstruct.getInteger("modulesDatabaseType", "", default=1),
            **optConstruct.getString("moduleName", "The Name of the PV Module", required=True,  default=""),
            **optConstruct.getFloat("lossesIrradiation", "The losses due to irradiation. in % (0-100)", default=1.0),
            **optConstruct.getFloat("lossesDCDatasheet", "The losses due to the datasheet. in % (0-100)", default=2.0),
            **optConstruct.getFloat("lossesDCCables", "The losses due to the DC cables. in % (0-100)", default=0.0),
            **optConstruct.getBoolean("useInverterDatabase", "Flag to indicate if the inverter database should be used.", default=False),
            **optConstruct.getString("inverterName", "The name of the inverter.", required=True, default=""),
            **optConstruct.getBoolean("useStandByPowerInverter", "Flag to indicate if the stand by power of the inverter should be used. Otherwise a constant value of 'inverterEta' is used.", default=False),
            **optConstruct.getFloat("inverterEta", "The efficiency of the inverter. as factor (0-1)", default=0.92)
        }