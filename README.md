﻿# **SoDeLe - Solar Simulation Made Easy**

SoDeLe is part of the QuaSi project [http://www.quasi-software.org](http://www.quasi-software.org).

![Sodele Logo](fig/Sodele_logo.JPG)

## **Name and purpose**

*SoDeLe* is a simple python-based tool that can calculate energy profiles of photovoltaik (PV) plants. They are calculated for specific PV modules combined with a specific inverter and a given orientation of the PV modules for a specified weather file. *SoDeLe* uses the python library [pvlib](https://doi.org/10.21105/joss.00884). The required weather input files have to be provided as EPW-standard (EnergyPlus© weather file) or as .dat weather data files from the German Weather Service (DWD) (see below for available sources).

With the provided GUI implemented in Excel, up to 10 differently oriented PV modules can be simulated separately. There is a simple and an advanced input interface. *SoDeLe* can also be used directly in python or the precompiled .exe can be called with the required input file (JSON format). For futher details, see the description below. 

The name *SoDeLe* is an acronyme for "Solarsimulation denkbar leicht" in German, what can be translatet to "solar simulation made easy". "Sodele" is a swabian word that could be translated to "Lets start!", which is an allusion to the speed required for the energy transition toward renewables.

## **Usage of *SoDeLe***
To simply use *SoDeLe*, no python installation or any other installation is required. *SoDeLe* can be used either from two different Excel-GUIs or from calling the `SoDeLe.exe` directly from the terminal while providing an input file in JSON format. The two possible ways to use *SoDeLe* without python are described below.

### **Using *SoDeLe* with the provided Excel UI (german only)**
**Requirements:** Excel 2016 or 365 (other versions were not tested) running on Windows.

There are two different Excel input files, both of which access the same computing core:

- `Sodele_Input_DE_extended.xlsm`: This is the detailed input interface with many different setting options for experienced users. Here, module connections and specific DC-AC inverters can be selected. This is great if a PV plant should be simulated that is already planned in detail. Note that the choice of the specific inverter model and the interconnection of the modules with the inverter have to match the specifications of the inverter and the modules!
- `Sodele_Input_DE_simplified.xlsm`: The simplified input interface reduces the range of possible PV-Moduls to three representative modules. Here, no specific AC-DC inverter is used, but a constant AC-DC efficiency instead. Therefore, significantly fewer inputs are required while keeping the results accurate. Usually, the simplified input is enough to calculate the energy output of a planned PV-System and much less mistakes can be made with the selection and interconnection of the system.

**Usage**
- In order to use *SoDeLe* with one of the Excel GUIs, download the content of the folder `precompiled_with_frontend`. Here, the two different GUIs as well as the precompiled `SoDeLe.exe` and a source folder with the required databases are located. Best performance results can be achieved if the files are saved locally to your computer. 
- After opening one of the two input interfaces, macros must be activated in Excel. Depending on the security settings of your Windows system, you may need to right-click on the .xlsm file, select preferences and check the tickbox "allow access" in the tab "general". 
- Then, a weather file must be selected via the "Browse" button (.epw or .dat, for details see below).
- After entering all necessary parameters, the simulation can be started via the "Start Simulation" button. Loading the program then takes a few seconds. In the opening console window, information about the simulation process and the chosen weather data set is displayed, allowing for a control of the chosen location.
- As a result, energy profiles for each of the simulated PV plans as well as for all of them and some key performance values are given in the Excel-based output file that opens automatically. Additionally, annual profiles of each PV system as well as the sum of all PV systems are plotted and saved to the output folder. Optionally, they can be openend in order to provide some interactivity. Note that the result file is only written after the plots were closed!

**Note (extended input only):** The inverters are sometimes only designed for small capacities. With large or many or too few modules or an inappropriate connection of the modules, a very poor overall efficiency can result. Therefore, it is also possible to specify a constant inverter efficiency - in this case, the calculation of the inverter losses from DC to AC by pvlib is bypassed.

### **Using *SoDeLe.exe* with a custom input file**

The executable can also be started directly from the command prompt with the path to the input file as argument: `cd /to/current/path/` followed by `SoDeLe.exe simulatePv -i path/to/Input.json`. Note that the `src` folder in `precompiled_with_frontend` has to be in the same directory as the `SoDeLe.exe`.

The JSON input file has to be structured in the following format:

```json
{
  "PhotovoltaicPlants": [
    {
    "surfaceAzimuth": 180, 
    "surfaceTilt": 30, 
    "modulesPerString": 115, 
    "stringsPerInverter": 1, 
    "numberOfInverters": 1, 
    "albedo": 0.2, 
    "moduleInstallation": 1, 
    "modulesDatabaseType": 2, 
    "moduleName": "AXITEC_AC_410MH_144V", 
    "inverterName": "ABB__MICRO_0_25_I_OUTD_US_208__208V_", 
    "useStandByPowerInverter": false, 
    "useInverterDatabase": false, 
    "inverterEta": 0.92, 
    "lossesIrradiation": 1, 
    "lossesDCDatasheet": 2, 
    "lossesDCCables": 0
    }
    ... optionally followed by more PV plants with the same structure
  ],
  "weatherData": {
    "latitude": 0,  
    "longitude": 0,
    "weatherDataFile": "./docs/WeatherFile.epw"
  },
  "showPlots": true
}
```

Note that the `moduleName` and the `inverterName` has to match the internal name of the databases used in pvlib. They are provided in the extended Excel GUI including some technical parameters. Note that even if `useInverterDatabase = false`, a valid inverter name has to be given to make pvlib work correctly. For the `weatherData`, the latitude and longitude are only needed if a request to the (commercial) DIETER service is performed. Otherwise, the path to a local weather file has to be given. All input parameter for each `PhotovoltaicPlant` are described below:

- `surfaceAzimuth`: azimuth angle of the PV modules (0Â° = north, 90Â° = east, 180Â° = south 270Â° = west)
- `surfaceTilt`: tilt angle of the PV modules (0Â° = flat on the earth, 90Â° = means vertically)
- `modulesPerString`: the number of modules that are connected to one string (series connection)
- `stringsPerInverter`: the number of strings that are connected to one inverter (parallel connection of strings)
- `numberOfInverters`: total number of inverters (the number of modules is then numberOfInverters * stringsPerInverter * modulesPerString)
- `albedo`: the albedo coefficient to determine the reflexion of the surroundings (default = 0.2)
- `moduleInstallation`: installation type of the modules:
    - 1: good air ventilation at the backside of the module and backcover out of glas
    - 2: good air ventilation at the backside of the module and backcover out of polymer
    - 3: module connected close to a roof, backcover out of glas
    - 4: isolated backside of the module and backcover out of polymer
- `modulesDatabaseType`: type of the utilized database for PV modules data. The CEC database has significantly more and recent moduls while the SANDIA model is the more accurate one:
    - 1: SANDIA
    - 2: CEC 
- `moduleName`: internal name of the module specified in the SANDIA or CEC database. See the extended Excel input file for a complete list (hidden sheet) or the generated .txt files with the internal PV module names provided in `src\sodele\res\PV_Database\`.
- `inverterName`: internal name of the DC-AC inverter specified in the CEC database. See the extended Excel input file for a complete list (hidden sheet) or the generated .txt files with the inverter internal names provided in `src\sodele\res\PV_Database\`.
- `useStandByPowerInverter`: flag if the standby energy of the inverter should be used (true/false)
- `useInverterDatabase`: flag if an inverter of the database should be used. If false, a constant AC-DC efficiency will be used (true/flase). Note: Even if this is false, a valid name of an inverter has to be given at `inverterName` in order to enable pvlib to work correctly.
- `inverterEta`: efficency of the DC-AC conversion, only if `useInverterDatabase=false`
- `lossesIrradiation`: additional losses due to missmatch of solar standard spectrum (in percent, default = 1)
- `lossesDCDatasheet`: additional losses to reduce the efficiency of the components as the parameter in the databases are measured under ideal conditions with new components (in percent, default = 2)
- `lossesDCCables`: ohmic losses in the cables (DC side, related to STC, in percent, default = 0)

## **Installation of python and usage of *SoDeLe* with python**
With an installed python environment, the python script can also be started directly from python, which allows for faster calculation. 

**Installation of python**

We recommend using a virtual environment. The required steps to work with *SoDeLe* from python are described below in short form:

- install the Python >= 3.12 from [https://www.python.org/downloads/](https://www.python.org/downloads/)
- navigate to the folder where you want to clone the repository
- clone repository to the local folder: `git clone git@github.com:QuaSi-Software/SoDeLe.git`
- create the virtual environment: `cd /path/to/local/sodele/repo/folder` and `python -m venv .venv`
- activate the virtual environment: `source .venv/bin/activate` (Linux) or `.\.venv\Scripts\activate` (Windows)
- install poetry (if not already installed): `pip install poetry`
- install the required packages: `poetry install` or with dev packages `poetry install --with dev`

**Usage of *SoDeLe* with Python**

With a python environment set up, *SoDeLe* can be run directly from python. Several input commands are available:

Running *SoDeLe* with the command `simulatePv` will run the PV simulation from a given input file in json format (see above for how to create an input file, an example is provided in `docs/testInput.json`) The following parameters should be used to call *SoDeLe*:
```
cd  <path/to/local/sodele/repo/folder> 
export PYTHONPATH=$PYTHONPATH:./src
<path/to/python.exe> bin/app.py simulatePv --input_json [or simply -i] <path/to/input.json>
```

To manually built the `SoDeLe.exe`, run `python buildAsExe.py` in your locally cloned repository. A new executable will be created in the folder `/dist`, named `app.exe`, which can be renamed to `SoDeLe.exe` to be called by the Excel-GUI or by the console as described above.

**Updating the PV module and inverter database** 

The databases with the parameters for the inverters and PV modules, stored in `src\sodele\res\PV_Database\`, can be updated using the data provided by the *System Advisor Model (SAM)* by *National Renewable Energy Laboratory*, available here: 
[https://github.com/NREL/SAM/tree/develop/deploy/libraries](https://github.com/NREL/SAM/tree/develop/deploy/libraries)

Running *SoDeLe* with the command `generatePVDatabase` will generate the databases for the PV modules and inverters as text files to integrate them into the GUI and to know the names of the internally used names by pvlib to enter them in the input json. 

The following function call can be used to generate the text files with the internal names of the PV modules and inverters:
```
<path/to/python.exe> <path/to/sodele/bin/app.py> generatePVDatabase --path [or simply -p] <path/to/database/folder>
```
The databases for the PV modules and the invertes have to be named as `CEC_Modules.csv` and `CEC_Inverters.csv` and have to be saved in the folder path given with the argument `--path`.


## **Weather data**
Accurate weather datasets are the basis for the PV simulation. Weather data can be read in by *SoDeLe* as both .epw and .dat files:

- EPW (EnergyPlus© weather file) is a standardized weather file format defined by EnergyPlus©. For further details see [https://designbuilder.co.uk/cahelp/Content/EnergyPlusWeatherFileFormat.htm](https://designbuilder.co.uk/cahelp/Content/EnergyPlusWeatherFileFormat.htm). EPW weather files for specific locations around the world as typical meteorological year (TMY) can be downloaded from different sources. An overview of free sources for EPW weather files can be found [here]([here](https://designbuilder.co.uk/cahelp/Content/FreeWeatherData.htm)).
- The .dat files are a specific file format of the German Weather Service. They provide typical meteorologiacal weather data for 2015 as well as a future projection for 2045 in a high spacial resolution for Germany. The weather files can be downloaded for free and can be imported directly in *SoDeLe*. The .dat files are avaiable at the German Weather Service's Climate Consulting module [https://kunden.dwd.de/obt/](https://kunden.dwd.de/obt/). Note that a free registration is required to access the data.

**Preprocessing of weather data in *SoDeLe*:**

In order to achieve correct results of the PV simulation, the convention of the weather files has to be correct. For EPW files, the solar radiation given at a specified time stamp is the sum of the radiation of the past hour. In order to be align with the convention of pvlib, the time stamp of EWP files is shifted by 30 minutes. The start of the internal timestamp is therefore always at 00:30 local time. 

As in the .dat files the direct normal radiation is not given, it is precalculated using functionalities of pvlib to determine the position of the sun. Here, also a timeshift is performed bevorhand to make sure that the radiation data is assigned to the correct time stamp and therefore to the correct position of the sun. This is important especially for facade-mounted PV modules. To check the accuracy of the time stamp shift, two PV plants facing towards a west and an east facade can be simulated and their annual irradiation have to be compared. If there is a deviation of > 15 %, the time stamp is usually wrong.


Requirements for DWD-dat file (corresponds to the output format of the DWD Climate Consulting module as of 01/2025):

- Measurement values are averages of the last time step
- There must be exactly 8760 measurement values in one file (--> hourly resolution, no leap year)
- Current as well as future test reference data sets can be used
- Time zone of the measurements is GMT+1 (CET, without consideration of summer/winter time)
- First data point must be on January 1 at 01:00 (will then be shifted to 00:30)
- Section with measurement data must begin with "***"
- The header must have the following format:
```
    - 1 ...
    - 2 Rechtswert        : 3936500 Meter
    - 3 Hochwert          : 2449500 Meter
    - 4 Hoehenlage        : 450 Meter ueber NN 
    - ...
    - 7 Art des TRY       : mittleres Jahr
    - 8 Bezugszeitraum    : 1995-2012
    - ...
```

**Note:** For the location-specific reference years of the DWD, a systematic deviation in the irradiation of the east and west facades (respective bevor and after noon) was found. The further east a location in Germany is, the greater the annual irradiation on an east facade (or in the morning bevore 12am). Conversely, the further west a location in Germany, the greater the annual sum of irradiation on a west facade (or in the afternon after 12am). The deviation is found to be up to +/- 15 %. The deviation of the radiation corresponds to a time shift of +/- 10 minutes of the time axis. This systematic error has not yet been taken into account and should be further investigated.


## Data source

The presets of the albedo coefficients provided in the Excel-GUI originate from the [SANDIA PV Performance Modeling Collaborative (PVPMC) - Modeling Guide](https://pvpmc.sandia.gov/modeling-guide/1-weather-design-inputs/plane-of-array-poa-irradiance/calculating-poa-irradiance/poa-ground-reflected/albedo/) and from [Wikipedia](https://en.wikipedia.org/wiki/Albedo).

The coefficients for the PV Modules and Inverters are from the [System Advisor Model (SAM) by National Renewable Energy Laboratory](https://github.com/NREL/SAM/tree/develop/deploy/libraries) and from the [pvlib repository](https://github.com/pvlib/pvlib-python/tree/main/pvlib/data).

The included weather files originates from the [Klimaberatungsmodul](https://kunden.dwd.de/obt/) of the German Weather Service (DWD) converted using the [EnergyPlus© Weather Converter](https://bigladdersoftware.com/epx/docs/8-3/auxiliary-programs/using-the-weather-converter.html).

The licenses are included in the respecitve folders.
