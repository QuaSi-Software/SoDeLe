import os

import numpy as np
import pandas as pd
import pvlib

from pathlib import Path
from sodele.Config import logging


def generatePvLibDatabase(basePath):
    """
    Generates the PV database for the PVLib library.

    :param basePath:    The base path.
    :type basePath:     str
    :return:
    """
    modules_path = f"{basePath}/CEC_Modules.csv"
    inverters_path = f"{basePath}/CEC_Inverters.csv"

    if not os.path.exists(modules_path):
        logging().warning(f"Fehler: Der Pfad zur PV-Moduldatenbank wurde nicht gefunden unter {modules_path}. Der Dateiname muss CEC_Modules.csv sein.")
        assert False

    if not os.path.exists(inverters_path):
        logging().warning(f"Fehler: Die Inverterdatenbank wurde nicht gefunden unter {inverters_path}. Der Dateiname muss CEC_Inverters.csv sein.")
        assert False

    PV_modules = pvlib.pvsystem.retrieve_sam(name=None, path=modules_path)
    PV_inverters = pvlib.pvsystem.retrieve_sam(name=None, path=inverters_path)

    # write to txt file
    PVModules_names = pd.DataFrame(np.array(PV_modules.columns.values))

    current_date = pd.Timestamp.now()
    current_date = current_date.strftime("%Y-%m-%d")
    txt_filename = f"{current_date}_PV_Modulnamen.txt"
    # path name
    writePath_Modules = Path(basePath) / txt_filename

    with open(writePath_Modules, 'w') as f:
        OutputData_asString = PVModules_names.to_string(header=False, index=False)
        f.write(OutputData_asString)

    # write to txt file
    PVInverter_names = pd.DataFrame(np.array(PV_inverters.columns.values))
    txt_filename = f"{current_date}_PV_Inverter.txt"
    # path name
    writePath_Inverter = Path(basePath) / txt_filename

    with open(writePath_Inverter, 'w') as f:
        OutputData_asString = PVInverter_names.to_string(header=False, index=False)
        f.write(OutputData_asString)

    logging().info(f"The internal names of PV modules and inverters were written to {writePath_Modules} and {writePath_Inverter}.")


if __name__ == "__main__":
    generatePvLibDatabase("./src/sodele/res/PV_Database")
