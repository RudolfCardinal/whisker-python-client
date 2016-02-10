#!/usr/bin/env python3
# demo_simple_whisker_client.py

# =============================================================================
# Imports, and configure logging
# =============================================================================

import logging
from attrdict import AttrDict
from datetime import datetime
import dataset
from whisker.colourlog import configure_logger_for_colour
from whisker.convenience import (
    load_config_or_die,
    connect_to_db_using_attrdict,
    insert_and_set_id,
    ask_user,
    save_data
)
# *** # import whisker.twisted

logger = logging.getLogger(__name__)
configure_logger_for_colour(logger)

# =============================================================================
# Constants
# =============================================================================

TASKNAME = "mytask"  # no spaces; we'll use it in a filename

# =============================================================================
# Load config; establish database connection; ask the user for anything else
# =============================================================================

logger.info("Asking user for config filename")
config = load_config_or_die()
db = connect_to_db_using_attrdict(config.database_url, show_url=True)

# These are our tables. They will be autocreated.
session_table = db['session']
trial_table = db['trial']
summary_table = db['summary']

# Any additional user input required?
num_trials = ask_user("Number of trials", default=10, type=int, min=1)

# =============================================================================
# Set up task and go
# =============================================================================

session = AttrDict(
    start=datetime.now(),
    subject=config.subject,
    session=config.session,
    num_trials=num_trials
)
insert_and_set_id(session_table, session)  # save to database
print("session: {}".format(repr(session)))

for t in range(1, num_trials + 1):
    trial = AttrDict(
        session_id=session.id,  # foreign key
        trial_num=t
    )
    trial.responded = True
    insert_and_set_id(trial_table, trial)  # save to database

# =============================================================================
# All done. Calculate summaries. Save data from this session to new CSV files.
# =============================================================================

# Retrieve all our trials. (There may also be many others in the database.)
trials = trial_table.find(session_id=session.id)

# Calculate some summary measures
summary = AttrDict(
    session_id=session.id,  # foreign key
    n_responded=sum(t.responded for t in trials)
)
insert_and_set_id(summary_table, summary)  # save to database

# Save data. (Since the session and summary objects are single objects, we
# encapsulate them in a list.)
save_data("session", [session], timestamp=session.start, taskname=TASKNAME)
save_data("trial", trials, timestamp=session.start, taskname=TASKNAME)
save_data("summary", [summary], timestamp=session.start, taskname=TASKNAME)
