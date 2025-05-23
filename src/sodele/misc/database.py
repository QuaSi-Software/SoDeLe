import os
from typing import Tuple

SODELE_ROOT = f"{os.getcwd()}/src/sodele"
RES_PREFIX = f"{SODELE_ROOT}/res/PV_Database"

def get_database_paths(modules_database_type: int) -> Tuple[str, str]:
    """
    Returns the database paths for the given modules database type.

    :param modules_database_type:     The type of the modules database. (1 = Sandia, 2 = CEC)
    :return:                        (ModuleDatabase, InverterDatabase)
    """

    if modules_database_type == 1:
        moduleDatabasePath = f"{RES_PREFIX}/220225_Sandia_Modules.csv"
        inverterDatabasePath = f"{RES_PREFIX}/221115_CEC_Inverters.csv"
        return moduleDatabasePath, inverterDatabasePath

    elif modules_database_type == 2:
        moduleDatabasePath = f"{RES_PREFIX}/221115_CEC_Modules.csv"
        inverterDatabasePath = f"{RES_PREFIX}/221115_CEC_Inverters.csv"
        return moduleDatabasePath, inverterDatabasePath

    else:
        raise ValueError(f"Unknown modules database type: {modules_database_type}")
