#!/usr/bin/env python3

"""
this runs around 10pm, and decides whether to dump excess
charge to the grid. There is typically around 25-40% of charge by then,
ie we need to get rid of between 20% and 35% of capacity.
1kW will shed 15% in 90 mins ; 2kW will shed 30%
"""

from givenergy import (
    GivEnergyApi,
    DISCHARGE_START,
    DISCHARGE_END,
    CHARGE_POWER,
    DISCHARGE_POWER,
    ENABLE_DC_DISCHARGE
)

# config

# 1% of battery capacity, as Watt-minutes
# eg 9.5kWh => 9.5 * 1000 * 1/100 * 60 = 95 * 60 = 5700
BATTERY = 5700

TARGET = 6  # target SoC after about 1.5 hours
READONLY = False
START = 22 * 60   # start time-of-day in minutes

# want to discharge between 1kW and 2kW in about 1.5 hours
# 1kW is 1000Wm/min, so 1% takes 5700/1000 = 5.7mins (ie 100% takes 5.7*100/60 = 9.5 hours)
# 2kW is 2000Wm/min, so 1% takes 5700/2000 = 2.8mins

def main():
    api = GivEnergyApi('discharge.py')
    latest = api.get_latest_system_data()
    current = latest['battery']['percent']

    delta = current - TARGET
    if delta > 30: delta = 30

    # excess energy is delta * BATTERY

    if current < 10:
        # normal consumption is about 3% per hour, so
        # it will lose 6% by 2230 anyway, so don't need
        # to bother
        discharge = 950
        mins = 0
    elif delta <= 15:
        # adjust elapsed time at 950W
        # should probably make a small adjustment to account for the base load
        # after it finishes this discharge.
        discharge = 1050
        mins = BATTERY * delta // discharge
    else:
        # calculate required power to drain in 90 mins
        mins = 90
        discharge = delta * BATTERY // 90  # 5700Wm/90m = 63W  ; delta=15% gives 950W

    end=START+mins
    if READONLY:
        print(f"power={discharge}, mins={mins}")
    else:
        # set a default charge power of 2400W now - just in case the
        # offpeak script fails later on. If SoC is down around 10%,
        # I'll be wanting to refill roughly 90% of battery in 5 hours.
        api.modify_setting(CHARGE_POWER, value=2400)

        if mins > 0:
            # The inverter actually discharges about 100W more than set,
            # so reduce the calculated value by that much
            api.modify_setting(DISCHARGE_POWER, value=discharge-100)
            api.modify_setting(DISCHARGE_START, value='%02d:%02d' % (START // 60, START % 60))
            api.modify_setting(DISCHARGE_END, value='%02d:%02d' % (end // 60, end % 60))
            api.modify_setting(ENABLE_DC_DISCHARGE, value=True)
        
if __name__ == "__main__":
    main()
