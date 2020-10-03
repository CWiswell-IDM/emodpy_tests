import json
import sys
import os

CURRENT_DIRECTORY = os.path.dirname(__file__)
LIBRARY_PATH = os.path.join(CURRENT_DIRECTORY, "..", "site-packages")  # Need to site_packages level!!!
sys.path.insert(0, LIBRARY_PATH)  # Very Important!
sys.path.append( os.path.join( CURRENT_DIRECTORY, ".." ) )

import shutil

import emod_api.schema.get_schema as get_schema
import emod_api.config.default_from_schema as default
from emod_api.schema_to_class import ReadOnlyDict
from emod_api.config import default_from_schema_no_validation as dfs
import build_my_campaign as bmc  # loaded to Assets/site-packages

def param_custom_cb( config ):
    config.parameters.Campaign_Filename = "import_pressure.json"
    config.parameters.Enable_Interventions = 1
    config.parameters.Simulation_Duration = 365
    config.parameters.Infectious_Period_Constant = 10.444444
    config.parameters.Incubation_Period_Constant = 10.444444
    config.parameters.Base_Infectivity_Constant = 10.444444
    return config

def make_config( camp_filename ):
    default.write_default_from_schema( "Assets/schema.json" )
    config = dfs.get_config_from_default_and_params( "default_config.json", param_custom_cb )
    config["parameters"]["Campaign_Filename"] = camp_filename
    with open( "config_from_emodapi.json", "w" ) as config_file:
        json.dump( config, config_file, indent=4, sort_keys=True )
    return "config_from_emodapi.json"

def application(config_filename="config.json", debug=True): 
    shutil.copy( "Assets/schema.json", "schema.json" )
    camp_filename = bmc.set_random_campaign_file()
    return make_config( camp_filename )


if __name__ == "__main__":
    # execute only if run as a script
    application("config.json")
