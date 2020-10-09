#!/usr/bin/env python

import pathlib # for a join
from functools import partial  # for setting Run_Number. In Jonathan Future World, Run_Number is set by dtk_pre_proc based on generic param_sweep_value...

# idmtools ...
from idmtools.assets import Asset, AssetCollection  #
from idmtools.builders import SimulationBuilder
from idmtools.core.platform_factory import Platform
from idmtools.entities.experiment import Experiment
from idmtools_platform_comps.utils.python_requirements_ac.requirements_to_asset_collection import RequirementsToAssetCollection
from idmtools_models.templated_script_task import get_script_wrapper_unix_task

# emodpy
from emodpy.emod_task import EMODTask
from emodpy.utils import EradicationBambooBuilds
from emodpy.bamboo import get_model_files

from covid_ghana import params
from covid_ghana import manifest

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

implicit_config_set_fns = [] # This may not be needed when I'm done with what I'm doing now.

def update_sim_bic(simulation, value):
    simulation.task.config.parameters.Base_Infectivity_Exponential = value*params.R0 / 8.0
    return {"Base_Infectivity": value}

def update_sim_random_seed(simulation, value):
    simulation.task.config.parameters.Run_Number = value
    return {"Run_Number": value}


def print_params():
    """
    Just a useful convenience function for the user.
    """
    # Display exp_name and nSims
    # TBD: Just loop through them
    print("exp_name: ", params.exp_name)
    print("nSims: ", params.nSims)

def set_param_fn(config): 
    """
    This function is a callback that is passed to emod-api.config to set parameters The Right Way.
    """
    config.parameters.Enable_Vital_Dynamics = 0 
    config.parameters.Immune_Downsample_Min_Age = 0.0
    config.parameters.Immune_Threshold_For_Downsampling = 1.0e-5
    config.parameters.Base_Individual_Sample_Rate = 0.1
    config.parameters.Relative_Sample_Rate_Immune = 0.1

    #config.parameters.Enable_Infection_Rate_Overdispersion = 1 # implicit
    #config.parameters.Infection_Rate_Overdispersion = 2.1  This is demographics TBD
    #  (daily amount of shedding; R0 = this_value*mean_shedding_duration)
    config.parameters.Base_Infectivity_Exponential = params.R0 / 8.0

    config.parameters.Incubation_Period_Gaussian_Mean = 4.0
    config.parameters.Incubation_Period_Gaussian_Std_Dev = 1.0
    config.parameters.Infectious_Period_Shape = 2.0
    config.parameters.Infectious_Period_Scale = 4.0
    config.parameters.Symptomatic_Infectious_Offset = 2.0
    config.parameters.Enable_Immunity = 1

    config.parameters.Migration_Pattern = 'SINGLE_ROUND_TRIPS'
    config.parameters.Regional_Migration_Roundtrip_Duration = 0.0
    config.parameters.Regional_Migration_Roundtrip_Probability = 0.0

    config.parameters.Enable_Spatial_Output = 1 # this should be implicit
    config.parameters.Spatial_Output_Channels = [ "Prevalence" ]
    config.parameters.Enable_Property_Output = 1
    config.parameters.Enable_Demographics_Reporting = 0

    config.parameters.Simulation_Duration = 365

    for fn in implicit_config_set_fns:
        config = fn( config )
    return config

def build_camp():
    """
    Build a campaign input file for the DTK using emod_api.
    Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
    """
    import emod_api.campaign as camp
    import emodpy_covid.interventions.covid_vaccine as cv # will move to emodpy_covid
    import emodpy_covid.interventions.complex_import as ci # will move to emodpy_measles

    # This isn't desirable. Need to think about right way to provide schema (once)
    cv.schema_path = manifest.schema_file 
    ci.schema_path = manifest.schema_file
    print(f"Telling emod-api to use {manifest.schema_file} as schema.")
    
    # importation pressure
    event = cv.SimpleSample1( timestep=0 )
    camp.add( event, first=True )

    # routine immunization
    event = cv.SimpleSample2( timestep=365, coverage=0.5 )
    camp.add( event )

    event = ci.ComplexImportationEvent(dips=[1. / 10], durs=[20 * 365], timestep=0)
    camp.add( event )

    # We are saving and reloading. Maybe there's an even better way? But even an outbreak seeding does not belong in the EMODTask.  
    filename = "campaign.json"
    camp.save( filename )
    print( f"Check for valid campaign file at: {filename}." )

    return filename

def build_demog():
    """
    Build a demographics input file for the DTK using emod_api.
    Right now this function creates the file and returns the filename. If calling code just needs an asset that's fine.
    Also right now this function takes care of the config updates that are required as a result of specific demog settings. We do NOT want the emodpy-disease developers to have to know that. It needs to be done automatically in emod-api as much as possible.
    TBD: Pass the config (or a 'pointer' thereto) to the demog functions or to the demog class/module.

    """
    import emodpy_covid.demographics.CovidDemographics as Demographics
    import emod_api.demographics.DemographicsTemplates as DT

    population = 1e5
    num_nodes = 10
    tag = "Covid Ghana Demo"
    demog = Demographics.from_synth_pop( tot_pop=population, num_nodes=num_nodes, id_ref=tag )
    DT.SimpleSusceptibilityDistribution( demog, meanAgeAtInfection=2.5 )
    DT.AddSeasonalForcing( demog, start=100, end=330, factor=1.0 )
    demog.AddAgeDependentTransmission( Age_Bin_Edges_In_Years=[0, 1, 2, -1], TransmissionMatrix=[[0.2, 0.4, 1.0], [0.2, 0.4, 1.0], [0.2, 0.4, 1.0]] )
    demog.generate_file() # TBD: user shouldn't have to think about files

    import emod_api.migration.Migration as mig
    mig_file = mig.from_synth_pop( pop=population, num_nodes=num_nodes, id_ref=tag )
    return "demographics.json", mig_file 

def general_sim( erad_path, ep4_scripts ):
    """
    This function is designed to be a parameterized version of the sequence of things we do 
    every time we run an emod experiment. 
    """
    print_params()

    # Create a platform
    # Show how to dynamically set priority and node_group
    platform = Platform("SLURM") 
    pl = RequirementsToAssetCollection( platform, requirements_path=manifest.requirements )

    # create EMODTask 
    print("Creating EMODTask (from files)...")
    camp_path = build_camp()
    params.base_infectivity = 0.2
    task = EMODTask.from_default2(config_path="my_config.json", eradication_path=manifest.eradication_path, campaign_path=camp_path, schema_path=manifest.schema_file, param_custom_cb=set_param_fn, ep4_custom_cb=None, demog_builder=build_demog )

    print("Adding asset dir...")
    task.common_assets.add_directory(assets_directory=manifest.assets_input_dir)

    # Set task.campaign to None to not send any campaign to comps since we are going to override it later with
    # dtk-pre-process.
    print("Adding local assets (py scripts mainly)...")

    if ep4_scripts is not None:
        for asset in ep4_scripts:
            pathed_asset = Asset(pathlib.PurePath.joinpath(manifest.ep4_path, asset), relative_path="python")
            task.common_assets.add_asset(pathed_asset)

    # Create simulation sweep with builder
    builder = SimulationBuilder()
    builder.add_sweep_definition( update_sim_random_seed, range(params.nSims) )

    # create experiment from builder
    experiment  = Experiment.from_builder(builder, task, name=params.exp_name) 

    # The last step is to call run() on the ExperimentManager to run the simulations.
    experiment.run(wait_until_done=True, platform=platform)

    #other_assets = AssetCollection.from_id(pl.run())
    #experiment.assets.add_assets(other_assets)

    # Check result
    if not experiment.succeeded:
        print(f"Experiment {experiment.uid} failed.\n")
        exit()

    print(f"Experiment {experiment.uid} succeeded.")

    # Save experiment id to file
    with open("COMPS_ID", "w") as fd:
        fd.write(experiment.uid.hex)
    print()
    print(experiment.uid.hex) 
    

def run_test( erad_path ):
    general_sim( erad_path, manifest.my_ep4_assets )

if __name__ == "__main__":
    # TBD: user should be allowed to specify (override default) erad_path and input_path from command line
    plan = EradicationBambooBuilds.CI_GENERICLINUX
    get_model_files( plan, manifest )
   
    run_test( manifest.eradication_path )
