#!/usr/bin/python3

# this runs just before and just after the off-peak period
# It assumes the target charge % has already been set,
# and chooses an appropriate charge rate to spread the
# charge over the whole 6-hour period

import sys
from datetime import date
import time
from givenergy import GivEnergyApi

# registers
CHARGE_POWER=72
DISCHARGE_POWER=73
CHARGE_LIMIT=77

def offpeak(api):
    # calculate required charging power
    latest = api.get_latest_system_data()
    current = latest['battery']['percent']
    target = api.read_setting(CHARGE_LIMIT)
    delta = target - current

    # battery is 9.5kWh - round up to 10kWh
    # off-peak is 6 hours
    # => want (delta / 100) * 10000Wh / 6h = delta * 16.67 (Watts)
    # Round up a little to be on the safe side.
    # Arbitrarily choose min charge rate of 500W
    # which will deliver 3kWh, or 30%, in 6 hours.
    # Note also that inverter tends to add about 180W over set rate anyway.
    charge = 500 if delta <= 30 else delta * 17
    
    # set discharge quite low:
    #  if already above target, don't really want to discharge
    #  IOG might extend charging beyond normal cheap hours. House demand is
    #  minimal until 7am, but if car is charging, don't let it take
    #  too much from battery
    # Note that min discharge is about 300W anyway, and it may
    # at at least 100 to whatever goes here.
    discharge = 250
        
    print(f'Current={current}, target={target} => charge={charge}, discharge={discharge}')
    return [charge, discharge]

def main():
    api = GivEnergyApi('offpeak.py')

    # Two modes of operation:
    #  'before' - calculate charge power based on current and target SoC
    #  'after'  - restore daytime settings. IOG we charge overnight
    #    and export most solar, so keep a low charge rate.`

    if sys.argv[1] == 'before':
        (charge, discharge) = offpeak(api)
    elif sys.argv[1] == 'after':
        print('Restoring full power for daytime')
        charge=500
        discharge=3600
    else:
        print('Usage: %s before|after' % (sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    api.modify_setting(CHARGE_POWER, value=charge)
    api.modify_setting(DISCHARGE_POWER, value=discharge)

main()
