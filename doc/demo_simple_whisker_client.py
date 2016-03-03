#!/usr/bin/env python
# demo_simple_whisker_client.py

# =============================================================================
# Imports, and configure logging
# =============================================================================

import logging
from attrdict import AttrDict
from datetime import datetime
from twisted.internet import reactor
from whisker.logging import configure_logger_for_colour
from whisker.constants import (DEFAULT_PORT,
                               CMD_REPORT_NAME,
                               CMD_TEST_NETWORK_LATENCY,
                               CMD_TIMER_SET_EVENT,
                               CMD_TIMESTAMPS)
from whisker.convenience import (load_config_or_die,
                                 connect_to_db_using_attrdict,
                                 insert_and_set_id,
                                 ask_user,
                                 save_data)
from whisker.twistedclient import WhiskerTask

log = logging.getLogger(__name__)
configure_logger_for_colour(log)

log.setLevel(logging.DEBUG)  # debug-level logging for this file...
logging.getLogger("whisker").setLevel(logging.DEBUG)  # ... and for Whisker

# =============================================================================
# Constants
# =============================================================================

TASKNAME_SHORT = "countpings"  # no spaces; we'll use it in a filename
TASKNAME_LONG = "Ping Counting Task"

# Our tables. They will be autocreated. (NOTE: do not store separate copies of
# table objects, as they can get out of sync as new columns area created.)
SESSION_TABLE = 'session'
TRIAL_TABLE = 'trial'
SUMMARY_TABLE = 'summary'


# =============================================================================
# The task itself
# =============================================================================

class MyWhiskerTask(WhiskerTask):
    def __init__(self, config, db, session):
        """Here, we initialize the task, and store any relevant variables."""
        super().__init__()  # call base class init
        self.config = config
        self.db = db
        self.session = session
        self.trial_num = 0

    def fully_connected(self):
        """At this point, we are fully connected to the Whisker server."""
        print("Task running.")
        period_ms = 1000
        self.command(CMD_TIMESTAMPS, "on")
        self.command(CMD_REPORT_NAME, TASKNAME_LONG)
        self.send(CMD_TEST_NETWORK_LATENCY)
        self.command(CMD_TIMER_SET_EVENT, period_ms,
                     self.session.num_pings - 1, "TimerFired")
        self.command(CMD_TIMER_SET_EVENT,
                     period_ms * (self.session.num_pings + 1),
                     0, "EndOfTask")

    def incoming_event(self, event, timestamp=None):
        """An event has arrived from the Whisker server."""
        # timestamp is the Whisker server's clock time in ms; we want real time
        now = datetime.utcnow()
        print("Event: {e} (timestamp {t}, real time {n})".format(
            e=event, t=timestamp, n=now.isoformat()))
        # We could do lots of things at this point. But let's keep it simple:
        if event == "EndOfTask":
            reactor.stop()  # stops Twisted and thus network processing
        else:
            trial = AttrDict(
                session_id=self.session.id,  # important foreign key
                trial_num=self.trial_num,
                event="Ping!",
                received=True,  # now we're just making things up...
                when=now,
            )
            insert_and_set_id(self.db[TRIAL_TABLE], trial)  # save to database
            self.trial_num += 1
            log.info("{} pings received so far".format(self.trial_num))


# =============================================================================
# Load config; establish database connection; ask the user for anything else
# =============================================================================

log.info("Asking user for config filename")
config = load_config_or_die(
    mandatory=['database_url'],
    defaults=dict(server='localhost', port=DEFAULT_PORT),
    log_config=True  # send to console (NB beware security of database URLs)
)
db = connect_to_db_using_attrdict(config.database_url)

# Any additional user input required?
num_pings = ask_user("Number of pings", default=10, type=int, min=1)
dummy = ask_user("Irrelevant: Heads or tails", default='H', options=['H', 'T'])

# =============================================================================
# Set up task and go
# =============================================================================

session = AttrDict(start=datetime.now(),
                   subject=config.subject,
                   session=config.session,
                   num_pings=num_pings)
insert_and_set_id(db[SESSION_TABLE], session)  # save to database
log.info("Off we go...")
task = MyWhiskerTask(config, db, session)
task.connect(config.server, config.port)
reactor.run()  # starts Twisted and thus network processing
log.info("Finished.")

# =============================================================================
# All done. Calculate summaries. Save data from this session to new CSV files.
# =============================================================================

# Retrieve all our trials. (There may also be many others in the database.)
# NOTE that find() returns an iterator (you get to iterate through it ONCE).
# Since we want to use this more than once (below), use a list.
trials = list(db[TRIAL_TABLE].find(session_id=session.id))

# Calculate some summary measures
summary = AttrDict(
    session_id=session.id,  # foreign key
    n_pings_received=sum(t.received for t in trials)
)
insert_and_set_id(db[SUMMARY_TABLE], summary)  # save to database

# Save data. (Since the session and summary objects are single objects, we
# encapsulate them in a list.)
save_data("session", [session], timestamp=session.start,
          taskname=TASKNAME_SHORT)
save_data("trial", trials, timestamp=session.start,
          taskname=TASKNAME_SHORT)
save_data("summary", [summary], timestamp=session.start,
          taskname=TASKNAME_SHORT)
