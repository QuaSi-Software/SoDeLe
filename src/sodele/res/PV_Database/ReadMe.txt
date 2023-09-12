PV Module and Inverter Database from (general):
CEC: 	https://github.com/NREL/SAM/tree/develop/deploy/libraries
SANDIA: https://github.com/pvlib/pvlib-python/tree/main/pvlib/data

Current database for CEC modules and inverters is from zip-file archive SAM version 2020.11.29 (more modules there than in the repository):
CEC: https://sam.nrel.gov/photovoltaic/pv-cost-component.html
--> see screenshot as well

To update database:
- download new module database from SAM website, SAM GitHub repository or PVlib GitHub repository and update path to new database in input file of PVlib.
- check .csv for duplicates - pvlib will bring an error message if douplicates are present, find and delete them in .csv file
- run pvlib with flag "Konsenausgabe aller Module" = True to get all internal names (txt files with internal names will be generated both for inverters and modules)
- update internal names and description of modules/inverters in hidden excel sheet of input file; description has to be generated from .csv file, e.g. [name, area, rated power]. You can use \sourcecode\221121_Create_ModuleInverterNamex.xlsx to generate names.
- update formulas in Excel input file(s) to cover whole database in hidden excel sheet (e.g. dropdows)