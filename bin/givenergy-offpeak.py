#!/usr/bin/python3

"""
this runs just before and just after the off-peak period
It assumes the target charge % has already been set,
and chooses an appropriate charge rate to spread the
charge over the whole offpeak period
"""

import sys
from givenergy import GivEnergyApi

# registers
CHARGE_POWER=72
DISCHARGE_POWER=73
CHARGE_LIMIT=77     # the one set by app
CHARGE_LIMIT_1=101  # the one actually used by the inverter

def offpeak(api):
    """calculate required charging power"""
    latest = api.get_latest_system_data()
    current = latest['battery']['percent']
    target = api.read_setting(CHARGE_LIMIT)
    delta = target - current

    # copy target to the setting that the inverter actually applies
    api.modify_setting(CHARGE_LIMIT_1, value=target)

    # While I have 6 hours offpeak from 2330 to 0530, because the
    # cumulative metering for battery in/out seems broken, I want
    # to delay the charging until after the daily counters get
    # reset at midnight. Also, allowing battery to idle at low SoC
    # may rebalance it. So charging is for 5 hours from 0030 to 0530.

    # battery is 9.5kWh - round up to 10000 for convenience
    # => want (delta / 100) * 10000Wh / 5h = delta * 20 (Watts)
    # Arbitrarily choose min charge rate of 500W which will
    # deliver 2.5kWh, or 25%, in 5 hours.
    # Note also that inverter tends to add about 180W over set rate anyway.
    charge = 500 if delta <= 25 else delta * 20

    # set discharge quite low:
    #  if already above target, don't really want to discharge
    #  IOG might extend charging beyond normal cheap hours. House demand is
    #  minimal until 7am, but if car is charging, don't let it take
    #  too much from battery
    # Note that min discharge is about 300W anyway, and it may
    # add at least 100 to whatever goes here.
    discharge = 250

    print(f'Current={current}, target={target} => charge={charge}, discharge={discharge}')
    return [charge, discharge]

def main():
    api = GivEnergyApi('offpeak.py')

    # Two modes of operation:
    #  'before' - calculate charge power based on current and target SoC
    #  'after'  - restore daytime settings. IOG we charge overnight
    #    and export most solar, so keep a low charge rate.`
    # But need high enough charge rate to prevent clipping.   

    if sys.argv[1] == 'before':
        (charge, discharge) = offpeak(api)
    elif sys.argv[1] == 'after':
        print('Restoring full power for daytime')
        charge=1000
        discharge=3600
    else:
        print('Usage: %s before|after' % (sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    api.modify_setting(CHARGE_POWER, value=charge)
    api.modify_setting(DISCHARGE_POWER, value=discharge)

if __name__ == "__main__":
    main()
