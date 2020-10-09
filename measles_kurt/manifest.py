#
# This is a user-modifiable Python file designed to be a set of simple input file and directory settings that you can choose and change.
#

import os

requirements = "measles_kurt/requirements.txt"
# The script is going to use this to store the downloaded schema file. Create 'Assets' directory or change to your preferred (existing) location.
schema_file="measles_kurt/Assets/schema.json"
# The script is going to use this to store the downloaded Eradication binary. Create 'stash' directory or change to your preferred (existing) location.
eradication_path="measles_kurt/stash/Eradication"
# Create 'Assets' directory or change to a path you prefer. idmtools will upload files found here.
assets_input_dir="measles_kurt/Assets"
ep4_path="measles_kurt/ep4"
PARAM_PATH = os.path.abspath('measles_kurt/param_dict.json')
