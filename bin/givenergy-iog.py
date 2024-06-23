#!/usr/bin/env python3

# this runs around 5am to check for any car-charging activity.
# It sets the pause-start time to be after the last charging slot.

import os
import datetime

from givenergy import GivEnergyApi, PAUSE_START
from octopus import IOG

def main():
    givenergy = GivEnergyApi('iog')
    
    charging = IOG.getChargingSlots(givenergy.config)

    # assume 5:30 by default
    start = datetime.time(5, 30)
    
    # because they're sorted, only need to worry about
    # the last slot, and only if it's not complete
    if len(charging) > 0 and not charging[-1][3]:
        endslot = charging[-1][1].time()
        if start < endslot:
            start = endslot

    # Now we have our pause time
    pause = f'{start.hour:02d}:{start.minute:02d}'
    # print("setting pause start time to ", pause)
    givenergy.modify_setting(PAUSE_START, pause)

if __name__ == "__main__":
    main()
