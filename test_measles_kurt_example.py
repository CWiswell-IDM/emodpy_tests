#!/usr/bin/env python

import os 
import json
from functools import partial
from idmtools.assets import Asset, AssetCollection
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment

from emodpy.defaults import EMODSir # REMOVE
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import RequirementsToAssetCollection

# emodpy
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds
from emodpy.bamboo import get_model_files
from measles_kurt import manifest

import pdb

# ****************************************************************
# Features to support:
#
#  Read experiment info from a json file
#  Add Eradication.exe as an asset (Experiment level)
#  Add Custom file as an asset (Simulation level)
#  Add the local asset directory to the task
#  Use builder to sweep simulations
#  How to run dtk_pre_process.py as pre-process
#  Save experiment info to file
# ****************************************************************



# Function used to set config parameter and also add file to simulation
def param_update(simulation, param, value):
    simulation.task.transient_assets.add_asset(Asset(filename="idxStrFile.txt", content='{:05d}'.format(value)))
    return simulation.task.set_parameter(param, value)

def general_sim( erad_path ):
# Function specially set parameter Run_Number
    set_Run_Number = partial(param_update, param="Run_Number")

# Get experiment parameters from json file
    with open(manifest.PARAM_PATH) as f:
        param_dict = json.load(f)
    exp_name = param_dict['expName']
    nSims = param_dict['nSims']

# Display exp_name and nSims
    print('exp_name: ', exp_name)
    print('nSims: ', nSims)
# Create a platform
# Show how to dynamically set priority and node_group
    platform = Platform('SLURM')
    pl = RequirementsToAssetCollection( platform, requirements_path=manifest.requirements )

# create EMODTask from default
    #task = EMODTask.from_default( default=EMODSir(), eradication_path=erad_path )
    #task = EMODTask.from_default2(config_path="ignore_my_config.json", eradication_path=manifest.eradication_path, campaign_path=None, param_custom_cb=None, ep4_custom_cb=manifest.ep4_path)
    task = EMODTask.from_files(config_path=None, eradication_path=manifest.eradication_path, ep4_path=manifest.ep4_path, demographics_paths=None)

# Add the parameters dictionary as an asset
    param_asset = Asset(absolute_path=manifest.PARAM_PATH)
    task.common_assets.add_asset(param_asset)

# Add more asset from a directory
    assets_dir = 'measles_kurt/Assets'
    task.common_assets.add_directory(assets_directory=assets_dir)
    #task.is_linux = True
# set campaign to None to not sending any campaign to comps since we are going to override it later with
# dtk-pre-process, This is import step in COMPS2
    task.campaign = None


# Load campaign_template.json to simulation which used by dtk_pre_process.py
    campaign_template_asset = Asset(os.path.join(manifest.assets_input_dir, "campaign_template.json"))
    task.transient_assets.add_asset(campaign_template_asset)

# Create simulation sweep with builder
    builder = SimulationBuilder()
    builder.add_sweep_definition(set_Run_Number, range(nSims))

# Create an experiment from builder
    experiment = Experiment.from_builder(builder, task, name=exp_name)
    other_assets = AssetCollection.from_id(pl.run())
    experiment.assets.add_assets(other_assets)
# Run experiment
    platform.run_items(experiment)

# Wait experiment to finish
    platform.wait_till_done(experiment)

# Check result
    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")

# Save experiment id to file
    with open('COMPS_ID', 'w') as fd:
        fd.write(experiment.uid.hex)
    print()
    print(experiment.uid.hex)

def run_test( erad_path ):
    general_sim( erad_path )

if __name__ == "__main__":
    plan = EradicationBambooBuilds.CI_GENERICLINUX
    get_model_files( plan, manifest )

    run_test( manifest.eradication_path )
