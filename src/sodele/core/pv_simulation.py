import numpy as np
import pandas as pd
import pvlib
from typing import TypedDict

from sodele.interfaces.pv_results import PvResult, SodeleResults, PhotovoltaicResultsWrapper
from sodele.interfaces.pv_specifics import PhotovoltaicPlant
from sodele.interfaces.sodele_input import SodeleInput

import logging

logger = logging.getLogger("SoDeLe")


class PvPlantResults(TypedDict):
    energyProfile: list[float]
    surfaceArea: float
    sumOfEnergyPerYear: float


class DataframeResults(TypedDict):
    df_resultEnergyProfiles: pd.DataFrame
    energyProfileColumns: list[str]
    energyAreaProfileColumns: list[str]


class SummaryResults(TypedDict):
    df_summary: pd.DataFrame
    pvPlantColumns: list[str]


def calc_pv_power_profile(sodele_input: SodeleInput, current_pv_plant: PhotovoltaicPlant) -> PvPlantResults:
    """
    Calculates the PV power profile

    :param sodele_input:     the sodele input
    :param current_pv_plant:  the current PV
    :return:
    """
    # start calculation
    # load all available modules and inverters
    current_module, current_inverter = current_pv_plant.get_modules_and_inverters()

    module_installation_switch = {1: "open_rack_glass_glass", 2: "open_rack_glass_polymer", 3: "close_mount_glass_glass", 4: "insulated_back_glass_polymer"}

    module_installation_type = module_installation_switch[current_pv_plant.moduleInstallation]

    # set temperature model type
    temperature_model_parameters = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"][module_installation_type]

    # location parameter from epw file
    latitude = sodele_input.weatherData.latitude
    longitude = sodele_input.weatherData.longitude

    # set location for model chain1
    location = pvlib.location.Location(latitude, longitude)

    # set system for model chain
    system_mc = pvlib.pvsystem.PVSystem(
        surface_tilt=current_pv_plant.surfaceTilt,
        surface_azimuth=current_pv_plant.surfaceAzimuth,
        module_parameters=current_module,
        inverter_parameters=current_inverter,
        temperature_model_parameters=temperature_model_parameters,
        modules_per_string=current_pv_plant.modulesPerString,
        strings_per_inverter=current_pv_plant.stringsPerInverter,
        losses_parameters={
            # ohmic losses in % for dc_ohmic_model with respect to STC
            "dc_ohmic_percent": current_pv_plant.lossesDCCables,
            "soiling": 0,
            # losses in % for losses_model: watts
            "shading": 0,
            "snow": 0,
            "mismatch": current_pv_plant.lossesDCDatasheet,
            "wiring": 0,
            "connections": 0,
            "lid": 0,
            "nameplate_rating": 0,
            "age": 0,
            "availability": 0,
        },
    )

    # Note: watts sums up all losses, they are all handled the same!

    data_base_switch = {
        1: "sapm",
        2: "cec",
    }

    dc_model = data_base_switch[current_pv_plant.modulesDatabaseType]

    mc = pvlib.modelchain.ModelChain(system_mc, location, dc_model=dc_model, aoi_model="physical", dc_ohmic_model="dc_ohms_from_percent", losses_model="pvwatts")

    # calculate precipitate water as values in EWP-file are all zero and convert to dataframe
    if sodele_input.weatherData.df_weatherData is None:
        raise ValueError("No weather data available!")

    df_weather = sodele_input.weatherData.df_weatherData
    precipitable_water = pvlib.atmosphere.gueymard94_pw(df_weather["temp_air"].values, df_weather["relative_humidity"].values)
    precipitable_water_DF = pd.DataFrame(precipitable_water, columns=["precipitable_water"], index=df_weather["temp_air"].index)

    # create DataFrame of albedo
    albedo = pd.DataFrame(current_pv_plant.albedo * np.ones((df_weather["temp_air"].size, 1)), columns=["albedo"], index=df_weather["temp_air"].index)

    # create data frame with weather data including reduction factor as pvlib requests
    losses_irradiation = current_pv_plant.lossesIrradiation
    weather_data = [
        (1 - losses_irradiation / 100) * df_weather["ghi"],
        (1 - losses_irradiation / 100) * df_weather["dni"],
        (1 - losses_irradiation / 100) * df_weather["dhi"],
        df_weather["temp_air"],
        df_weather["wind_speed"],
        precipitable_water_DF["precipitable_water"],
        albedo["albedo"],
    ]

    weather = pd.concat(weather_data, axis=1)

    # run model chain with weather data
    mc.run_model(weather)

    # total amount of modules per PV system
    n_modules = current_pv_plant.numberOfInverters * current_pv_plant.stringsPerInverter * current_pv_plant.modulesPerString  # [piece]

    # inverter dc to alternate current
    if current_pv_plant.useInverterDatabase:
        # use inverter from sandia database
        inverterValue = pvlib.inverter.sandia(mc.results.dc["v_mp"], mc.results.dc["p_mp"], current_inverter)  # [W]
        pv_power_profile = current_pv_plant.numberOfInverters * inverterValue  # [W]
    else:
        # use single eta for inverter
        single_eta_value = mc.results.dc["p_mp"] * current_pv_plant.inverterEta  # [W]
        pv_power_profile = current_pv_plant.numberOfInverters * single_eta_value  # [W]

    # fill nan values of power profile with zero
    pv_power_profile = pv_power_profile.fillna(0)

    # limit to lower bound = 0 if standby power should be ignored
    if not current_pv_plant.useStandByPowerInverter:
        pv_power_profile[pv_power_profile < 0] = 0

    # calculate rated power of all installed modules to get specific energy generation within simulated time horizon
    modules_power_rated = 0
    if current_pv_plant.modulesDatabaseType == 1:
        # Sandia
        modules_power_rated = current_module.Impo * current_module.Vmpo * n_modules  # [W_peak]
        module_surface_area = current_module.Area * n_modules  # [m^2]
    elif current_pv_plant.modulesDatabaseType == 2:
        # CEC
        modules_power_rated = current_module.I_mp_ref * current_module.V_mp_ref * n_modules  # [W_peak]
        module_surface_area = current_module.A_c * n_modules  # [m^2]
    else:
        raise ValueError("Invalid value for modulesDatabaseType")

    # calculate energy profile from power profile
    pv_energy_profile = pv_power_profile.values * 8760 / pv_power_profile.size  # [Wh]

    return PvPlantResults(
        energyProfile=pv_energy_profile.tolist(),  # in [Wh]
        surfaceArea=module_surface_area,  # in [m^2]
        sumOfEnergyPerYear=pv_energy_profile.sum() / 1_000,  # in [kWh]
    )


def get_pv_gis_data(latitude: float, longitude: float) -> None:
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


def generate_energy_profile_data_frame(sodele_input: SodeleInput) -> DataframeResults:
    """
    Generates a pandas dataframe with the energy profiles of all photovoltaic plants in the sodeleInput object.

    :param sodele_input:     sodeleInput object

    :return: pd.DataFrame, energyProfileColumns, energyAreaProfileColumns,
    """
    energy_profile_columns = []
    energy_area_profile_columns = []
    surface_area_collector = []
    df_result_energy_profiles: pd.DataFrame = pd.DataFrame()
    for currentIdx, currentPVPlant in enumerate(sodele_input.photovoltaicPlants):
        energy_profile_column = f"PV-Anlage {currentIdx}: Energieprofile [kWh]"
        df_result_energy_profiles[energy_profile_column] = currentPVPlant.energyProfile
        energy_profile_columns.append(energy_profile_column)
        surface_area_collector.append(currentPVPlant.surfaceArea)

        energy_area_profile_column = f"PV-Anlage {currentIdx}: Flächenspezifisches Energieprofil [kWh/m^2]"
        df_result_energy_profiles[energy_area_profile_column] = currentPVPlant.energyProfileArea
        energy_area_profile_columns.append(energy_area_profile_column)

    all_column = "PV-Energieprofil aller Anlagen [kWh]"
    df_result_energy_profiles[all_column] = df_result_energy_profiles[energy_profile_columns].sum(axis=1)
    all_area_column = "Flächenspezifisches PV-Energieprofil aller Anlagen [kWh/m^2]"
    df_result_energy_profiles[all_area_column] = (df_result_energy_profiles[energy_profile_columns].sum(axis=1)) / np.sum(surface_area_collector)  # type: ignore

    return DataframeResults(df_resultEnergyProfiles=df_result_energy_profiles, energyProfileColumns=energy_profile_columns, energyAreaProfileColumns=energy_area_profile_columns)


def generate_summary_data_frame(sodele_input: SodeleInput) -> SummaryResults:
    """
    Generates a pandas dataframe with the summary of all photovoltaic plants in the sodeleInput object.

    :param sodele_input:    sodeleInput object
    :return:           pd.DataFrame, pvPlantColumns
    """
    energy_profile_collector = []
    energy_profile_area_collector = []
    surface_area_collector = []
    system_kwp_collector = []
    for currentPVPlant in sodele_input.photovoltaicPlants:
        energy_profile_collector.append(currentPVPlant.energyProfile)
        energy_profile_area_collector.append(currentPVPlant.energyProfileArea)
        surface_area_collector.append(currentPVPlant.surfaceArea)
        system_kwp_collector.append(currentPVPlant.systemKWP)

    # sum over all energy profiles
    energy_profile_sum = np.sum(np.array(energy_profile_collector), axis=0)

    # specific energy yield of each system
    energy_per_system = np.sum(np.array(energy_profile_collector), axis=1)  # [kWh]
    energy_over_all_systems = np.sum(energy_profile_sum)  # [kWh]
    energy_per_system_area = energy_per_system / np.array(surface_area_collector)  # [kWh/m^2]
    energy_over_all_systems_area = sum(energy_profile_sum) / np.sum(surface_area_collector)  # type: ignore  # [kWh/m^2]
    energy_kwp_per_system = energy_per_system / np.array(system_kwp_collector)  # [kWh/kWp]
    energy_kwp_over_all_systems = sum(energy_profile_sum) / np.sum(system_kwp_collector)  # type: ignore # [kWh/kWp]

    df_summary = pd.DataFrame()
    df_summary["Beschriebener Wert"] = ["Jahressumme Energieertrag [kWh]", "Leistungsspezifischer Jahresertrag [kWh/kWp]", "Flächenspezifischer Jahresertrag [kWh/m^2]"]

    pv_plant_columns = []
    for currentIdx, currentPVPlant in enumerate(sodele_input.photovoltaicPlants):
        column_name = f"PV-Anlage {currentIdx}"
        pv_plant_columns.append(column_name)
        sum_of_energy = energy_per_system[currentIdx]
        spec_energy_per_kwp = energy_kwp_per_system[currentIdx]
        spec_energy_per_area = energy_per_system_area[currentIdx]
        df_summary[column_name] = [sum_of_energy, spec_energy_per_kwp, spec_energy_per_area]

    result_column = "Ergebnis aller PV-Anlagen"
    df_summary[result_column] = [
        energy_over_all_systems,
        energy_kwp_over_all_systems,
        energy_over_all_systems_area,
    ]

    return SummaryResults(df_summary=df_summary, pvPlantColumns=pv_plant_columns)


def build_result_dict(sodele_input: SodeleInput, energy_results: DataframeResults, summary_results: SummaryResults) -> SodeleResults:
    """
    Builds a dictionary with the results of the simulation.

    :param sodele_input:        The sodele input
    :param energy_results:      The energy results
    :param summary_results:     The summary results
    :return:
    """

    # serialize the data to a json format
    single_pv_results: list[PvResult] = []

    df_result_energy_profiles = energy_results["df_resultEnergyProfiles"]
    energy_profile_columns = energy_results["energyProfileColumns"]
    energy_area_profile_columns = energy_results["energyAreaProfileColumns"]
    df_summary = summary_results["df_summary"]
    pv_plant_columns = summary_results["pvPlantColumns"]

    for pvIndex in range(len(sodele_input.photovoltaicPlants)):
        energy_profile = df_result_energy_profiles[energy_profile_columns[pvIndex]].tolist()
        energy_area_profile = df_result_energy_profiles[energy_area_profile_columns[pvIndex]].tolist()
        summary = df_summary[pv_plant_columns[pvIndex]].tolist()
        sum_of_energy_per_year = summary[0]
        work_specific_energy_per_year = summary[1]
        area_specific_energy_per_year = summary[2]

        single_pv_results.append(
            PvResult(
                EnergyProfile=energy_profile,
                EnergyAreaProfile=energy_area_profile,
                SumOfEnergyPerYear=sum_of_energy_per_year,
                WorkSpecificEnergyPerYear=work_specific_energy_per_year,
                AreaSpecificEnergyPerYear=area_specific_energy_per_year,
            )
        )

    energy_profile_of_all = df_result_energy_profiles.iloc[:, -2].tolist()
    energy_area_profile_of_all = df_result_energy_profiles.iloc[:, -1].tolist()
    summary_of_all = df_summary.iloc[:, -1].tolist()
    sum_of_energy_per_year_of_all = summary_of_all[0]
    work_specific_energy_per_year_of_all = summary_of_all[1]
    area_specific_energy_per_year_of_all = summary_of_all[2]

    summary_result = PvResult(
        EnergyProfile=energy_profile_of_all,
        EnergyAreaProfile=energy_area_profile_of_all,
        SumOfEnergyPerYear=sum_of_energy_per_year_of_all,
        WorkSpecificEnergyPerYear=work_specific_energy_per_year_of_all,
        AreaSpecificEnergyPerYear=area_specific_energy_per_year_of_all,
    )

    result = SodeleResults(
        PhotovoltaicResults=PhotovoltaicResultsWrapper(
            PhotovoltaicPlants=single_pv_results,
            SummaryOfAllPlants=summary_result,
        )
    )

    return result


def simulate_pv_plants(sodele_input: SodeleInput) -> tuple[SodeleResults, list[PhotovoltaicPlant]]:
    """
    Start the Simulation

    Read in the Input File, Read the Weather File, Perform the Calculation, Create the Output Figures and Safe the Output to the Outputfile
    :return:
    """

    if sodele_input.weatherData.adjustTimestamp:
        sodele_input.weatherData.adjust_time_stamp()

    if sodele_input.weatherData.recalculateDNI:
        if not sodele_input.weatherData.adjustTimestamp:
            logger.warning("Attention: Adjusting the time stamp without recalculating the direct normal radiation may result in an incorrect data record!")
        sodele_input.weatherData.recalculate_dni()

    logger.info(f"Calculate PV profiles and create graphs for {len(sodele_input.photovoltaicPlants)} PV system(s)..")

    # call CalcPVPowerProfile and write calculated energy profile to list
    for currentIdx, currentPVPlant in enumerate(sodele_input.photovoltaicPlants):
        results = calc_pv_power_profile(sodele_input, currentPVPlant)
        currentPVPlant.energyProfile = results["energyProfile"]
        currentPVPlant.surfaceArea = results["surfaceArea"]
        currentPVPlant.systemKWP = results["sumOfEnergyPerYear"]

    logger.info("Finished the Calculation")
    logger.info("preparing the Output")

    energy_results: DataframeResults = generate_energy_profile_data_frame(sodele_input)
    summary_results: SummaryResults = generate_summary_data_frame(sodele_input)

    # write the results
    if sodele_input.keep_files:
        filename = f"./tmp/{sodele_input.uuid}_pv_simulation.xlsx"
        with pd.ExcelWriter(filename, engine="xlsxwriter") as xlsxWriter:
            df_result_energy_profiles = energy_results["df_resultEnergyProfiles"]
            df_result_energy_profiles.to_excel(xlsxWriter, sheet_name="Energieprofile", index=False)
            df_summary = summary_results["df_summary"]
            df_summary.to_excel(xlsxWriter, sheet_name="Zusammenfassung", index=False)

    # serialize the data to a json format
    result: SodeleResults = build_result_dict(sodele_input, energy_results, summary_results)

    return result, sodele_input.photovoltaicPlants
