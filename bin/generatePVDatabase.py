import os

import pvlib
import numpy as np
import pandas as pd
import datetime


def generatePvLibDatabase():
    # get all the names of the modules and inverters via CEC
    PV_modules = pvlib.pvsystem.retrieve_sam('cecmod')
    PV_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')

    df_pv_modules = PV_modules.transpose()
    df_pv_inverters = PV_inverters.transpose()

    # convert the index column to a "Name" column
    df_pv_modules["Name"] = df_pv_modules.index
    df_pv_inverters["Name"] = df_pv_inverters.index

    # drop the index column
    df_pv_modules = df_pv_modules.reset_index(drop=True)
    df_pv_inverters = df_pv_inverters.reset_index(drop=True)

    # put the name column to the front
    df_pv_modules = df_pv_modules[["Name"] + [col for col in df_pv_modules.columns if col != "Name"]]
    df_pv_inverters = df_pv_inverters[["Name"] + [col for col in df_pv_inverters.columns if col != "Name"]]

    pv_modules_units_per_column = ";;;;;;m2;m;m;;A;V;A;V;A/K;V/K;C;V;A;A;Ohm;Ohm;%;%/K;;;"
    pv_inverters_units_per_column = "Units;V;W;W;W;V;1/W;1/V;1/V;1/V;W;V;A;V;V;;;"

    def generateName(col, unit):
        return f"{col} [{unit}]" if unit != "" else col

    # add the units to the columns
    df_pv_modules.columns = [generateName(col, unit) for col, unit in zip(df_pv_modules.columns, pv_modules_units_per_column.split(";"))]
    df_pv_inverters.columns = [generateName(col, unit) for col, unit in zip(df_pv_inverters.columns, pv_inverters_units_per_column.split(";"))]

    # save the dataframes to csv
    df_pv_modules.to_csv("./sodele/res/PV_Database/221115_CEC_Modules.csv", sep=";", index=False)
    df_pv_inverters.to_csv("./sodele/res/PV_Database/221115_CEC_Inverters.csv", sep=";", index=False)


if __name__ == "__main__":
    generatePvLibDatabase()
