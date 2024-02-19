#!/usr/bin/python3

"""
this runs around 8pm, and decides whether to dump excess
charge to the grid.
"""

from givenergy import GivEnergyApi

# registers
DISCHARGE_START=53
DISCHARGE_END=54
ENABLE_DISCHARGE=56
DISCHARGE_POWER=73

def main():
    api = GivEnergyApi('discharge.py')
    latest = api.get_latest_system_data()
    current = latest['battery']['percent']

    # if current is already < 40%, don't bother.

    if current < 40:
        print(f'{current}% - turning off discharge')
        api.modify_setting(ENABLE_DISCHARGE, value='false')
        return

    # target is very roughly 25% by 10:30pm (in case IOG schedules an
    # early charging slot).
    # Battery is 9.5kWh. Don't want to discharge faster than 2kW,
    # so that makes max discharge amount 50% in 2.5h, so if SoC is
    # more than 75%, round down.
    delta = 50 if current >= 75 else current - 25

    # excess energy is delta/100 * 9.5kWh
    #  = delta * 95 * 60 Watt-minutes (Wm)
    #  = delta * 5700 Wm
    # Don't want to reduce power much below 1kW, since that
    # is an upper-limit on evening power consumption. That
    # corresponds to about 25% of battery in 150 mins. So
    # that's our crossover point.
    if delta <= 25:
        # adjust elapsed time at 950W
        discharge = 950
        mins = 6 * delta  # 5700Wm/950W = 6mins ; 25% is 150 mins
    else:
        # calculate required power to drain in 150 mins
        mins = 150
        discharge = delta * 38  # 5700Wm/150m = 38W  ; delta=25% gives 950W

    # start time is 8pm = 1200 mins past midnight
    # end time is (1200+mins) mins past midnight
    end=1200+mins
    api.modify_setting(DISCHARGE_POWER, value=discharge)
    api.modify_setting(DISCHARGE_START, value='20:00')
    api.modify_setting(DISCHARGE_END, value='%02d:%02d' % (end // 60, end % 60))
    api.modify_setting(ENABLE_DISCHARGE, value='true')

if __name__ == "__main__":
    main()
