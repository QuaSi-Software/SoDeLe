from sodele.Helper.dictor import dictor
import sodele.Helper.optionsConcstructor as optConstruct


class PhotovoltaicConfig:
    """
    PhotovoltaicConfig class

    :param modulesDatabaseType:         The type of the modules database.
    :type modulesDatabaseType:          int

    :param modulesDatabasePath:         The path to the modules database. Will be set automatically.
    :type modulesDatabasePath:          str
    :param inverterDatabasePath:        The path to the inverter database. Will be set automatically.
    :type inverterDatabasePath:         str
    """

    def __init__(self, modulesDatabaseType: int):
        self.modulesDatabaseType = modulesDatabaseType
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

        return PhotovoltaicConfig(modulesDatabaseType)


    def serialize(self):
        """
        Serializes the photovoltaic config.

        :return: dict
        """
        return {
            "modulesDatabaseType": self.modulesDatabaseType,
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
        }