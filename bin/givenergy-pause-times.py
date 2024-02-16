#!/usr/bin/python3

"""
Sets pause start and end times from cmd line.
Needed because I want a gap in the pause around midday.
Could possibly try something like start=14:00, end=12:00,
but don't want to interfere with overnight charging from grid.
"""

import sys
from givenergy import GivEnergyApi

# registers
PAUSE_BATTERY=96
PAUSE_START=155
PAUSE_END=156

def main():
    api = GivEnergyApi('pause-times.py')

    if len(sys.argv) == 3:
        api.modify_setting(PAUSE_START, sys.argv[1])
        api.modify_setting(PAUSE_END,   sys.argv[2])
    else:
        print('Usage: %s start-time end-time' % (sys.argv[0]), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
