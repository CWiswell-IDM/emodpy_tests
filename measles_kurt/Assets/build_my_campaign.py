import emod_api.interventions.import_pressure as ip
import emodpy_measles.interventions.complex_import as ci
import emod_api.campaign as camp
import random
import numpy as np 
import os

KEY_CAMPAIGN_DURATIONS = "Durations"
KEY_CAMPAIGN_DIP = "Daily_Import_Pressures"
KEY_NODE_LIST = "Node_List"
MAX_DURATION = 800
NUM_OF_BUCKETS = np.random.randint(2, 10)
MAX_RATE = 20

#cwd = os.path.dirname(os.path.realpath(__file__))
cwd = "."
ip.schema_path = os.path.join( cwd, "schema.json" )

def generate_durations(length, max_duration):
    """
    generate a random list of durations(integer)
    :param length: length of the list
    :param max_duration: total duration of this list
    :return: list of durations
    """
    durations = []
    total_duration = 0
    for i in range(length):
        random_duration = random.random() + 1  # at least 1 day
        total_duration += random_duration
        durations.append(random_duration)
    ratio = max_duration / float(total_duration)
    durations = [int(x * ratio) for x in durations]
    durations[-1] = max_duration - sum(durations) + durations[-1]
    return durations


def generate_rates(length, max_rate):
    """
    generate a random list of rates(float)
    :param length: length of the list
    :param max_rate: maximum rate in thie list
    :return: list of rates
    """
    rates = []
    for i in range(length):
        random_max = random.random() * max_rate  # more randomness
        random_rate = random.random() * random_max
        rates.append(random_rate)
    return rates


def generate_random_node_list():
    random_list = []
    len_list = random.randint(2,5)
    for i in range(len_list):
        random_node = random.randint(1, 5)
        if random_node not in random_list:
            random_list.append(random_node)
    return sorted(random_list)


def set_random_campaign_file(campaign_filename="campaign.json", campaign_template_filename= "campaign_template.json", debug = False): 
    durations = generate_durations(NUM_OF_BUCKETS, MAX_DURATION)
    if sum(durations) != MAX_DURATION:
        print( "total duration is {0}, expected {1}.\n".format(sum(durations), MAX_DURATION))
    ip.durations = durations
    rates = generate_rates(NUM_OF_BUCKETS,MAX_RATE)
    ip.daily_import_pressures = rates
    ip.nodes = [ 3, 5, 7 ]
    print( "Calling ip.new_intervention_as_file." )
    #camp_filename = ip.new_intervention_as_file(1, campaign_filename)
    event = ip.new_intervention(1, durations, rates, [ 3, 5, 7 ] )
    camp.add( event )
    camp.save( campaign_filename )

    if debug:
        print("durations are : {}.\n".format(durations))
        print("daily inport pressures are : {}.\n".format(rates))
    return campaign_filename 

