#!/usr/bin/env python3
# yaml_example.py

from attrdict import AttrDict
import yaml

# Demo starting values; lots of ways of creating an AttrDict
config = AttrDict()
config.session = 3
config.stimulus_order = [3, 2, 1]
config.subject = "S1"

# Save
with open("yaml_config_demo.yaml", "w") as outfile:
    outfile.write(yaml.dump(config.copy()))  # write a dict, not an AttrDict

# Load
with open("yaml_config_demo.yaml") as infile:
    config = AttrDict(yaml.safe_load(infile))
