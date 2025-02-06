import os

import numpy as np
import pandas as pd
import pvlib

from pathlib import Path
import logging

logger = logging.getLogger("Sodele")


def generate_pv_lib_database(basePath: str) -> None:
    """
    Generates the PV database for the PVLib library.

    :param basePath:    The base path.
    :return:
    """
    modules_path = f"{basePath}/CEC_Modules.csv"
    inverters_path = f"{basePath}/CEC_Inverters.csv"

    if not os.path.exists(modules_path):
        logger.warning(f"Fehler: Der Pfad zur PV-Moduldatenbank wurde nicht gefunden unter {modules_path}. Der Dateiname muss CEC_Modules.csv sein.")
        assert False

    if not os.path.exists(inverters_path):
        logger.warning(f"Fehler: Die Inverterdatenbank wurde nicht gefunden unter {inverters_path}. Der Dateiname muss CEC_Inverters.csv sein.")
        assert False

    pv_modules = pvlib.pvsystem.retrieve_sam(name=None, path=modules_path)
    pv_inverters = pvlib.pvsystem.retrieve_sam(name=None, path=inverters_path)

    # write to txt file
    pv_modules_names = pd.DataFrame(np.array(pv_modules.columns.values))

    current_date_stamp = pd.Timestamp.now()
    current_date = current_date_stamp.strftime("%Y-%m-%d")
    txt_filename = f"{current_date}_PV_Modulnamen.txt"
    # path name
    write_path_modules = Path(basePath) / txt_filename

    with open(write_path_modules, "w") as f:
        output_data_as_string = pv_modules_names.to_string(header=False, index=False)
        f.write(output_data_as_string)

    # write to txt file
    pv_inverter_names = pd.DataFrame(np.array(pv_inverters.columns.values))
    txt_filename = f"{current_date}_PV_Inverter.txt"
    # path name
    write_path_inverter = Path(basePath) / txt_filename

    with open(write_path_inverter, "w") as f:
        output_data_as_string = pv_inverter_names.to_string(header=False, index=False)
        f.write(output_data_as_string)

    logger.info(f"The internal names of PV modules and inverters were written to {write_path_modules} and {write_path_inverter}.")


if __name__ == "__main__":
    generate_pv_lib_database("./src/sodele/res/PV_Database")
