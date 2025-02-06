from typing import Tuple


def get_database_paths(modules_database_type: int) -> Tuple[str, str]:
    """
    Returns the database paths for the given modules database type.

    :param modules_database_type:     The type of the modules database. (1 = CEC, 2 = Sandia)
    :return:                        (ModuleDatabase, InverterDatabase)
    """
    if modules_database_type == 1:
        moduleDatabasePath = "./src/sodele/res/PV_Database/220225_Sandia_Modules.csv"
        inverterDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Inverters.csv"
        return moduleDatabasePath, inverterDatabasePath

    elif modules_database_type == 2:
        moduleDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Modules.csv"
        inverterDatabasePath = "./src/sodele/res/PV_Database/221115_CEC_Inverters.csv"
        return moduleDatabasePath, inverterDatabasePath

    else:
        raise ValueError(f"Unknown modules database type: {modules_database_type}")
