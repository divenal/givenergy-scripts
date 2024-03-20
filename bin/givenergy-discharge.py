#!/usr/bin/env python3

"""
this runs around 8pm, and decides whether to dump excess
charge to the grid.
"""

from givenergy import GivEnergyApi, \
       DISCHARGE_START, DISCHARGE_END, CHARGE_POWER, DISCHARGE_POWER

def main():
    api = GivEnergyApi('discharge.py')
    latest = api.get_latest_system_data()
    current = latest['battery']['percent']

    # target is very roughly 10% by 10:30pm (in case IOG schedules an
    # early charging slot).
    # Battery is 9.5kWh. Don't want to discharge faster than 2kW,
    # so that makes max discharge amount 50% in 2.5h, so if SoC is
    # more than 60%, round down.
    delta = 50 if current >= 60 else current - 10

    # excess energy is delta/100 * 9.5kWh
    #  = delta * 95 * 60 Watt-minutes (Wm)
    #  = delta * 5700 Wm
    # Don't want to reduce power much below 1kW, since that
    # is an upper-limit on evening power consumption. That
    # corresponds to about 25% of battery in 150 mins. So
    # that's our crossover point.

    if current < 20:
        # normal consumption is about 3% per hour, so
        # it will lose 10% by 2230 anyway, so don't need
        # to bother
        discharge = 950
        mins = 0
    elif delta <= 25:
        # adjust elapsed time at 950W
        # should probably make a small adjustment to account for the base load
        # after it finishes this discharge.
        discharge = 950
        mins = 6 * delta  # 5700Wm/950W = 6mins ; 25% is 150 mins
    else:
        # calculate required power to drain in 150 mins
        mins = 150
        discharge = delta * 38  # 5700Wm/150m = 38W  ; delta=25% gives 950W

    # set a default charge power of 1000W now - just in case the
    # offpeak script fails later on. If SoC is down around 10%,
    # I'll be wanting to refill roughly 50% of battery in 5 hours.
    api.modify_setting(CHARGE_POWER, value=1000)

    # start time is 8pm = 1200 mins past midnight
    # end time is (1200+mins) mins past midnight
    end=1200+mins
    api.modify_setting(DISCHARGE_POWER, value=discharge)
    api.modify_setting(DISCHARGE_START, value='20:00')
    api.modify_setting(DISCHARGE_END, value='%02d:%02d' % (end // 60, end % 60))

if __name__ == "__main__":
    main()
