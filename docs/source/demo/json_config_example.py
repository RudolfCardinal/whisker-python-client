#!/usr/bin/env python
# json_example.py

import json

# Demo starting values
# config = {
#     "session": 3,
#     "stimulus_order": [3, 2, 1],
#     "subject": "S1"
# }

# or, equivalently:
config = dict(
    session=3,
    stimulus_order=[3, 2, 1],
    subject='S1'
)

# Save
with open("json_config_demo.json", "w") as outfile:
    json.dump(config, outfile,
              sort_keys=True, indent=4, separators=(',', ': '))

# Load
with open("json_config_demo.json") as infile:
    config = json.load(infile)
