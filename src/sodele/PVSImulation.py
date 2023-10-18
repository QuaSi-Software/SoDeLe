import numpy as np
import pandas as pd
import pvlib

from sodele.Config import logging, getConfig
from sodele.Objects.PhotovoltaicPlant import PhotovoltaicPlant
from sodele.Objects.SodeleInput import SodeleInput


def CalcPVPowerProfile(sodeleInput, currentPVPlant):
    """
    Calculates the PV power profile

    :param sodeleInput:     the sodele input
    :type sodeleInput:      SodeleInput
    :param currentPVPlant:  the current PV
    :type currentPVPlant:   PhotovoltaicPlant
    :return:
    """
    # start calculation
    # load all available modules and inverters
    current_module, current_inverter = currentPVPlant.getModulesAndInverters()

    moduleInstallationSwitch = {
        1: 'open_rack_glass_glass',
        2: 'open_rack_glass_polymer',
        3: 'close_mount_glass_glass',
        4: 'insulated_back_glass_polymer'
    }

    moduleInstallationType = moduleInstallationSwitch[currentPVPlant.moduleInstallation]

    # set temperature model type
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm'][moduleInstallationType]

    # location parameter from epw file
    latitude = sodeleInput.weatherData.latitude
    longitude = sodeleInput.weatherData.longitude

    # set location for model chain1
    location = pvlib.location.Location(latitude, longitude)

    # set system for model chain
    system_mc = pvlib.pvsystem.PVSystem(surface_tilt=currentPVPlant.surfaceTilt,
                                        surface_azimuth=currentPVPlant.surfaceAzimuth,
                                        module_parameters=current_module,
                                        inverter_parameters=current_inverter,
                                        temperature_model_parameters=temperature_model_parameters,
                                        modules_per_string=currentPVPlant.modulesPerString,
                                        strings_per_inverter=currentPVPlant.stringsPerInverter,
                                        losses_parameters={
                                            # ohmic losses in % for dc_ohmic_model with respect to STC
                                            'dc_ohmic_percent': currentPVPlant.lossesDCCables,
                                            'soiling': 0,
                                            # losses in % for losses_model: watts
                                            'shading': 0,
                                            'snow': 0,
                                            'mismatch': currentPVPlant.lossesDCDatasheet,
                                            'wiring': 0,
                                            'connections': 0,
                                            'lid': 0,
                                            'nameplate_rating': 0,
                                            'age': 0,
                                            'availability': 0
                                        })

    # Note: watts sums up all losses, they are all handled the same!

    dataBaseSwitch = {
        1: "sapm",
        2: "cec",
    }

    dc_model = dataBaseSwitch[currentPVPlant.modulesDatabaseType]

    mc = pvlib.modelchain.ModelChain(system_mc, location,
                                     dc_model=dc_model,
                                     aoi_model='physical',
                                     dc_ohmic_model="dc_ohms_from_percent",
                                     losses_model="pvwatts")

    # calculate precipitate water as values in EWP-file are all zero and convert to dataframe
    df_weather = sodeleInput.weatherData.df_weatherData
    precipitable_water = pvlib.atmosphere.gueymard94_pw(df_weather["temp_air"].values, df_weather["relative_humidity"].values)
    precipitable_water_DF = pd.DataFrame(precipitable_water, columns=['precipitable_water'], index=df_weather["temp_air"].index)

    # create DataFrame of albedo
    albedo = pd.DataFrame(currentPVPlant.albedo * np.ones((df_weather["temp_air"].size, 1)), columns=['albedo'], index=df_weather["temp_air"].index)

    # create data frame with weather data including reduction factor as pvlib requests
    losses_irradiation = currentPVPlant.lossesIrradiation
    weather_data = [(1 - losses_irradiation / 100) * df_weather['ghi'],
                    (1 - losses_irradiation / 100) * df_weather['dni'],
                    (1 - losses_irradiation / 100) * df_weather['dhi'],
                    df_weather["temp_air"],
                    df_weather["wind_speed"],
                    precipitable_water_DF['precipitable_water'],
                    albedo['albedo']]

    weather = pd.concat(weather_data, axis=1)

    # run model chain with weather data
    mc.run_model(weather)

    # total amount of modules per PV system
    n_modules = currentPVPlant.numberOfInverters * currentPVPlant.stringsPerInverter * currentPVPlant.modulesPerString  # [piece]

    # inverter dc to alternate current
    if currentPVPlant.useInverterDatabase:
        # use inverter from sandia database
        Pv_power_profile = currentPVPlant.numberOfInverters * pvlib.inverter.sandia(mc.results.dc['v_mp'], mc.results.dc['p_mp'], current_inverter)  # [W]
    else:
        # use single eta for inverter
        Pv_power_profile = currentPVPlant.numberOfInverters * mc.results.dc['p_mp'] * currentPVPlant.inverterEta  # [W]

    # fill nan values of power profile with zero
    Pv_power_profile = Pv_power_profile.fillna(0)

    # limit to lower bound = 0 if standby power should be ignored
    if not currentPVPlant.useStandByPowerInverter:
        Pv_power_profile[Pv_power_profile < 0] = 0

    # calculate rated power of all installed modules to get specific energy generation within simulated time horizon
    if currentPVPlant.modulesDatabaseType == 1:
        # Sandia
        modules_power_rated = current_module.Impo * current_module.Vmpo * n_modules  # [W_peak]
        module_surfaceArea = current_module.Area * n_modules  # [m^2]
    elif currentPVPlant.modulesDatabaseType == 2:
        # CEC
        modules_power_rated = current_module.I_mp_ref * current_module.V_mp_ref * n_modules  # [W_peak]
        module_surfaceArea = current_module.A_c * n_modules  # [m^2]
    else:
        raise ValueError('Invalid value for modulesDatabaseType')

    # calculate energy profile from power profile
    Pv_energy_profile = Pv_power_profile.values * 8760 / Pv_power_profile.size  # [Wh]

    return Pv_energy_profile / 1_000, module_surfaceArea, modules_power_rated / 1_000  # in [kWh], [m^2], [kWp]


def getPvGisData(latitude, longitude):
    """
    Returns the PVGIS data for the given latitude and longitude

    :param latitude:    The latitude of the location
    :type latitude:     float
    :param longitude:   The longitude of the location
    :type longitude:    float
    :return:
    """
    print(latitude, longitude)
    # PVGIS is currently not supported because of the high DWD data quality provided by Dieter
    raise NotImplementedError("PVGIS is not implemented yet!")

    # try:
    #    temp = pvlib.iotools.get_pvgis_tmy(latitude, longitude,
    #                                       outputformat='epw', usehorizon=False,
    #                                       startyear=2005, endyear=2016,
    #                                       map_variables=True, url='https://re.jrc.ec.europa.eu/api/v5_2/')
    #    weatherdata = [temp[0], temp[3]]
    # except Exception as e:
    #    print('Fehler: Der TRY-Datensatz von PVGIS konnte nicht heruntergeladen werden.')
    #    print('Fehlermeldung: ' + str(e))
    #    raise Exception("Fehler: Für den automatischen Bezug von TRY Wetterdaten von PVGIS müssen Latitute und Longitude angegeben sein!")
    #
    # # set flags for timeshift and recalculation of DNI
    # # Note: For PVGIS EPW TRY files of central europe, average timeshift is 75 minutes.
    # # Attention: This is not valid for worldwide data! E.g. in Aisa, timeshift has to be 0 minutes! (investigated in 12/2022)
    # general = {"latitude": latitude, "longitude": longitude}
    # PV_Powerprofile = {}
    # general.adjust_timestamp = True  # flag if weather data should be shiftete by timeshift
    # general.recalculate_DNI = True  # flag if direct normal iradiation should be recalculated
    # PV_Powerprofile.plotDNI = False  # flag if recalculated DNI should be plotted
    # general.timeshift = 75  # [min] Minutes to shift the weatherdatas time index.


def generateEnergyProfileDataFrame(sodeleInput):
    """
    Generates a pandas dataframe with the energy profiles of all photovoltaic plants in the sodeleInput object.

    :param sodeleInput:     sodeleInput object
    :type sodeleInput:      SodeleInput

    :return: pd.DataFrame, energyProfileColumns, energyAreaProfileColumns,
    """
    energyProfileColumns = []
    energyAreaProfileColumns = []
    df_resultEnergyProfiles = pd.DataFrame()
    for currentIdx, currentPVPlant in enumerate(sodeleInput.photovoltaicPlants):
        energyProfileColumn = f"PV-Anlage {currentIdx}: Energieprofile [kWh]"
        df_resultEnergyProfiles[energyProfileColumn] = currentPVPlant.energyProfile
        energyProfileColumns.append(energyProfileColumn)

        energyAreaProfileColumn = f"PV-Anlage {currentIdx}: Flächenspezifisches Energieprofil [kWh/m^2]"
        df_resultEnergyProfiles[energyAreaProfileColumn] = currentPVPlant.energyProfileArea
        energyAreaProfileColumns.append(energyAreaProfileColumn)

    df_resultEnergyProfiles["PV-Energieprofil aller Anlagen [kWh]"] = df_resultEnergyProfiles[energyProfileColumns].sum(axis=1)
    df_resultEnergyProfiles["Flächenspezifisches PV-Energieprofil aller Anlagen [kWh/m^2]"] = (df_resultEnergyProfiles[energyAreaProfileColumns].sum(axis=1)) / len(energyAreaProfileColumns)

    return df_resultEnergyProfiles, energyProfileColumns, energyAreaProfileColumns


def generateSummaryDataFrame(sodeleInput):
    """
    Generates a pandas dataframe with the summary of all photovoltaic plants in the sodeleInput object.

    :param sodeleInput:    sodeleInput object
    :type sodeleInput:     SodeleInput
    :return:           pd.DataFrame, pvPlantColumns
    """
    energyProfileCollector = []
    energyProfileAreaCollector = []
    surfaceAreaCollector = []
    systemKWPCollector = []
    for currentPVPlant in sodeleInput.photovoltaicPlants:
        energyProfileCollector.append(currentPVPlant.energyProfile)
        energyProfileAreaCollector.append(currentPVPlant.energyProfileArea)
        surfaceAreaCollector.append(currentPVPlant.surfaceArea)
        systemKWPCollector.append(currentPVPlant.systemKWP)

    # sum over all energy profiles
    energyProfileSum = np.sum(np.array(energyProfileCollector), axis=0)

    # specific energy yield of each system
    energyPerSystem = np.sum(np.array(energyProfileCollector), axis=1)  # [kWh]
    energyOverAllSystems = np.sum(energyProfileSum)  # [kWh]
    energyPerSystemArea = energyPerSystem / np.array(surfaceAreaCollector)  # [kWh/m^2]
    energyOverAllSystemsArea = sum(energyProfileSum) / np.sum(surfaceAreaCollector)  # [kWh/m^2]
    energyKWPPerSystem = energyPerSystem / np.array(systemKWPCollector)  # [kWh/kWp]
    energyKWPOverAllSystems = sum(energyProfileSum) / np.sum(systemKWPCollector)  # [kWh/kWp]

    df_summary = pd.DataFrame()
    df_summary["Beschriebener Wert"] = ["Jahressumme Energieertrag [kWh]",
                                        "Leistungsspezifischer Jahresertrag [kWh/kWp]",
                                        "Flächenspezifischer Jahresertrag [kWh/m^2]"]

    pvPlantColumns = []
    for currentIdx, currentPVPlant in enumerate(sodeleInput.photovoltaicPlants):
        columnName = f"PV-Anlage {currentIdx}"
        pvPlantColumns.append(columnName)
        sumOfEnergy = energyPerSystem[currentIdx]
        specEnergyPerKwp = energyKWPPerSystem[currentIdx]
        specEnergyPerArea = energyPerSystemArea[currentIdx]
        df_summary[columnName] = [sumOfEnergy, specEnergyPerKwp, specEnergyPerArea]

    resultColumn = "Ergebnis aller PV-Anlagen"
    df_summary[resultColumn] = [energyOverAllSystems,
                                energyKWPOverAllSystems,
                                energyOverAllSystemsArea, ]

    return df_summary, pvPlantColumns


def buildResultDict(sodeleInput,
                    df_resultEnergyProfiles, energyProfileColumns, energyAreaProfileColumns,
                    df_summary, pvPlantColumns):
    """
    Builds a dictionary with the results of the simulation.

    :param sodeleInput:                 sodeleInput object
    :type sodeleInput:                  SodeleInput
    :param df_resultEnergyProfiles:     pandas dataframe with the energy profiles of all photovoltaic plants
    :type df_resultEnergyProfiles:      pd.DataFrame
    :param energyProfileColumns:        list of column names of the energy profiles
    :type energyProfileColumns:         list
    :param energyAreaProfileColumns:    list of column names of the energy area profiles
    :type energyAreaProfileColumns:     list
    :param df_summary:                  pandas dataframe with the summary of all photovoltaic plants
    :type df_summary:                   pd.DataFrame
    :param pvPlantColumns:              list of column names of the photovoltaic plants
    :type pvPlantColumns:               list
    :return:
    """


    # serialize the data to a json format
    result = {
        "PhotovoltaicResults": {
            "PhotovoltaicPlants": [],
        }
    }

    for pvIndex in range(len(sodeleInput.photovoltaicPlants)):
        energyProfile = df_resultEnergyProfiles[energyProfileColumns[pvIndex]].tolist()
        energyAreaProfile = df_resultEnergyProfiles[energyAreaProfileColumns[pvIndex]].tolist()
        summary = df_summary[pvPlantColumns[pvIndex]].tolist()
        sumOfEnergyPerYear = summary[0]
        workSpecificEnergyPerYear = summary[1]
        areaSpecificEnergyPerYear = summary[2]

        result["PhotovoltaicResults"]["PhotovoltaicPlants"].append({
            "EnergyProfile": energyProfile,
            "EnergyAreaProfile": energyAreaProfile,
            "SumOfEnergyPerYear": sumOfEnergyPerYear,
            "WorkSpecificEnergyPerYear": workSpecificEnergyPerYear,
            "AreaSpecificEnergyPerYear": areaSpecificEnergyPerYear
        })

    energyProfileOfAll = df_resultEnergyProfiles.iloc[:, -2].tolist()
    energyAreaProfileOfAll = df_resultEnergyProfiles.iloc[:, -1].tolist()
    summaryOfAll = df_summary.iloc[:, -1].tolist()
    sumOfEnergyPerYearOfAll = summaryOfAll[0]
    workSpecificEnergyPerYearOfAll = summaryOfAll[1]
    areaSpecificEnergyPerYearOfAll = summaryOfAll[2]

    result["PhotovoltaicResults"]["SummaryOfAllPlants"] = {
        "EnergyProfile": energyProfileOfAll,
        "EnergyAreaProfile": energyAreaProfileOfAll,
        "SumOfEnergyPerYear": sumOfEnergyPerYearOfAll,
        "WorkSpecificEnergyPerYear": workSpecificEnergyPerYearOfAll,
        "AreaSpecificEnergyPerYear": areaSpecificEnergyPerYearOfAll
    }

    return result


def simulatePVPlants(sodeleInput):
    """
    Start the Simulation

    Read in the Input File, Read the Weather File, Perform the Calculation, Create the Output Figures and Safe the Output to the Outputfile

    :param sodeleInput: The configuration File
    :type sodeleInput: SodeleInput
    :return:
    """

    if not sodeleInput.weatherData.shouldAdjustTimestamp and sodeleInput.weatherData.shouldRecalculateDNI:
        logging().warning("Attention: Adjusting the time stamp without recalculating the direct normal radiation may result in an incorrect data record!")
        sodeleInput.weatherData.recalculateDNI()

    if sodeleInput.weatherData.shouldAdjustTimestamp and sodeleInput.weatherData.shouldRecalculateDNI:
        sodeleInput.weatherData.adjustTimeStamp(sodeleInput.weatherData.timeshiftInMinutes)
        sodeleInput.weatherData.recalculateDNI()

    logging().info("Calculate PV profiles and create graphs for " + str(sodeleInput) + " PV system(s)..")

    # call CalcPVPowerProfile and write calculated energy profile to list
    for currentIdx, currentPVPlant in enumerate(sodeleInput.photovoltaicPlants):
        results = CalcPVPowerProfile(sodeleInput, currentPVPlant)
        currentPVPlant.energyProfile = results[0].tolist()
        currentPVPlant.surfaceArea = results[1]
        currentPVPlant.systemKWP = results[2]
        currentPVPlant.calculateProfileMetrics()

    logging().info("Finished the Calculation")
    logging().info("preparing the Output")

    df_resultEnergyProfiles, energyProfileColumns, energyAreaProfileColumns = generateEnergyProfileDataFrame(sodeleInput)
    df_summary, pvPlantColumns = generateSummaryDataFrame(sodeleInput)

    # write the results
    if getConfig().KEEP_FILES:
        with pd.ExcelWriter("./tmp/example.xlsx", engine='xlsxwriter') as xlsxWriter:
            df_resultEnergyProfiles.to_excel(xlsxWriter, sheet_name="Energieprofile", index=False)
            df_summary.to_excel(xlsxWriter, sheet_name="Zusammenfassung", index=False)

    # serialize the data to a json format
    result = buildResultDict(sodeleInput,
                             df_resultEnergyProfiles, energyProfileColumns, energyAreaProfileColumns,
                             df_summary, pvPlantColumns)

    return result
