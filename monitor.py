#!/usr/bin/env python3

# monitor AC generation to avoid clipping if possible
# This is primarily about controlling battery charging, but
# keep an eye on discharging too:
# - when forcing discharge, I tend to reduce power. But I want it put
#   back up to max when in dynamic mode.
# - if AC generation maxes out during forced discharge (due to additional solar),
#   also want to reduce discharge rate.
# But it's complicated slightly because, of course, discharge might be
# just trying to cover house load.

import asyncio
from datetime import datetime
from gzip import GzipFile
import logging
import sys

from givenergy_modbus.client.client import Client
from givenergy_modbus.model.plant import Plant
from givenergy_modbus.model.register import HR, IR

_logger = logging.getLogger(__name__)

def remaining(now, ts):
    # time until end of timeslot

    t = ts.start
    ss = t.hour * 3600 + t.minute * 60 + ts.start.second
    t = ts.end
    es = t.hour * 3600 + t.minute * 60 + ts.start.second
    t = now
    ts = t.hour * 3600 + t.minute * 60 + ts.start.second

    # now is assumed to be in the timeslot
    if ts < es:
        return es - ts
    elif ss < es:
        # ts does not wrap midnight
        return 0
    else:
        # ts wraps midnight, so it's seconds until midnight
        # plus seconds until end
        return 3600 - ss + es
        

class MyPlant(Plant):

    # we are interested in when dp changes
    dpchanged = None

    def registers_updated(self, reg, count, values):
        if count == 1:
            # This is *usually* because a register has changed.
            # But note that retrieving a value through the cloud API does
            # seem to do a read of a single register.
            print(f'holding reg {reg} now {values[0]}')
            if int(reg) == 112:
                self.dpchanged = datetime.now()
            
async def monitor(zf = None):
    """
    Monitor the system for clipping, and adjust battery
    charging power as required.
    """
    # Only interested in a subset of registers, and no batteries
    registers = {IR(0),  HR(0), HR(60), HR(300)}
    plant = MyPlant(registers=registers, num_batteries=0)
    client = Client(sys.argv[1], 8899, recorder=zf, plant=plant)

    # moving averages for solar, generation export, and battery
    sma = 0
    gma = 0
    ema = 0
    bma = 0

    # saw-tooth decaying things for solar and generation
    sdecay = 0
    gdecay = 0

    # seconds since last adjustment.
    # Use -60 initially to avoid doing anything until moving averages
    # have settled down
    elapsed = -60

    await client.connect()
    
    # "%5d %6.1f %6.1f  %5d %6.1f %6.1f   %5d %5d %6.1f %6.1f  %s %s %d %d"
    # solar, sma, sdecay,
    # gen, gma, gdecay,
    # export, ema,
    # battery, bma, inverter.temp_inverter_heatsink,
    #                  cp, paused, elapsed, delay)
    print("-------solar-------   --------gen-------    --export--   ---------battery----------   -temp- -time-")

    # first time through, the refresh includes the HR's
    # subsequently, set to False to include only the IR subset
    # Note that we have to repeat the register subset since other
    # registers might appear if other applications discover them.
    full = True
    while True:
        await client.refresh_plant(full_refresh=full, registers = registers)
        full = False

        inverter = plant.inverter
        solar = inverter.p_pv1 + inverter.p_pv2
        gen = inverter.p_inverter_out
        export = inverter.p_grid_out
        battery = inverter.p_battery

        # use a very fast ma to filter spikes
        factor = .75  #  if gen > gma else .1
        sma = solar*factor + sma*(1-factor)
        gma = gen*factor + gma*(1-factor)
        ema = export*factor + ema*(1-factor)
        bma = battery*factor + bma*(1-factor)

        # then a sawtooth sort of thing
        sdecay = sma if sma >= sdecay else sdecay * .95 + sma * .05
        gdecay = gma if gma >= gdecay else gdecay * .95 + gma * .05

        # choose a default refresh time.
        # 30s seems a good choice when solar is in the vicinity of 5kW
        # Go out to 5 mins (300s) when solar is close to 0.
        # so (5555 - solar) / 18.5 gives the right sort of shape:
        #  300.27 when solar is 0
        #   30 when solar is 5000

        sun = solar if solar > sdecay else sdecay
        delay = 30 if sun > 5000 else (5555 - sun) / 18.5
        assert delay >= 30

        # for charging, we control two parameters : pause-battery-charging, and charging-power
        # charging power is a percentage of battery size,
        # so unit size is about 95W. But there's about 250W
        # extra (so 250W when cp is 0).
        # Data-fitting suggests that power = x * 97.5 + 185, but
        # when x = 0, it behaves like 1.
        # Could also think of it as approx 95 * (x + 2)
        # When paused, it tends to show as charging at 28W or so.
        # (Or -28, since the input register is battery discharge power.)
        #
        # discharge power is a bit more regular:
        #  dp=0 gives discharge power of around 55W
        #  otherwise it's about (dp*97.5W)

        paused = inverter.battery_pause_mode
        dp = inverter.battery_discharge_limit
        cp = inverter.battery_charge_limit

        # "effective" charging power is 0 if paused, else cp.
        # (We try to avoid setting cp to 0 because it behaves same as 1.)
        # This gets set to -dp if we are forced_discharge
        ecp = 0 if paused else cp

        # Now figure out what we need to change.
        delta = 0
        forced_discharge = False
        requests = []
        commands = client.commands

        # secondary job: discharge power

        if dp is not None and dp < 40:
            # discharge power is not at max. Should we fix that?
            # (Anything above about 36 is effectively the max of 3.6kW)
            # I almost always use slot 1 for forced discharges.
            ds1 = inverter.discharge_slot_1
            now = datetime.now()
            tnow = now.time()

            forced_discharge = ds1 is not None and tnow in ds1
            if forced_discharge:
                _logger.debug("we are inside discharge slot 1")
                # Note that the inverter tends to overshoot end of
                # discharge by a minute or two.
                # Fudge things by pretending that dp has only just changed,
                # and ensuring we wake up 30 seconds before the end of
                # the discharge period.
                # That way, we won't restore it until 5 mins after the end of
                # the discharge period
                plant.dpchanged = now
                dt = remaining(tnow, ds1) - 30
                if delay > dt: delay = dt
                ecp = -dp
            elif plant.dpchanged is not None and (now - plant.dpchanged).total_seconds() < 300:
                # It has been changed in the last 5 minutes.
                # Assume this is in anticipation of a forced discharge.
                _logger.debug("dp has only recently been changed...")
                if delay > 30: delay = 30
            elif bma > 200 and ema > 100:
                _logger.info("we seem to be exporting from battery - not sure why")
                delay = 30
            else:
                _logger.info("setting dp back up to 50")
                requests.append(commands.write_named_register('battery_discharge_limit', 50))


        # clipping avoidance (charging)
        if gma > 4800:
            print('* need to increase cp')
            if gen > 4900:
                # The instantaneous reading suggests we are close to
                # clipping, but that hasn't yet fed into the moving average.
                # Do a bigger jump and reduce delay
                delta = 3
                delay = 10
            else:
                delta = 1
        elif gen >= 4800:
            # might just be a transient - don't increase yet
            delay = 15
        elif gdecay >= 4500 or gen >= 4500:
            # not time to reduce power yet. (A transient increase is not
            # a good reason increase charging power, but is a good reason
            # to defer reducing it for a cycle.)
            pass  # keep things as they are
        elif ema < -250:
            # we seem to be importing ???
            # defer any decisions for another cycle
            _logger.debug('* importing %d ?', ema)
        elif elapsed < 60:
            # not long since last reduction - just be patient
            pass
        elif not paused:
            # Time to reduce power. We want to get gdecay back up to around 4500
            delta = int((gdecay - 4500) / 97.5)
            delay = 30


        _logger.info("%5d %6.1f %6.1f  "
                     "%5d %6.1f %6.1f  "
                     "%5d %6.1f  "
                     "%5d %6.1f %s %s %s %3d   "
                     "%4.1f   "
                     "%d %d",
                     solar, sma, sdecay,
                     gen, gma, gdecay,
                     export, ema,
                     battery, bma, cp, dp, paused, inverter.battery_percent,
                     inverter.temp_inverter_heatsink,
                     elapsed, delay)

        if delta != 0:
            # Now turn that into an action
            # TODO: consider that there might be a forced discharge in the
            # morning. If so, would need to reduce discharge rate

            _logger.debug('ecp is %d, delta is %d')
            wcp = ecp + delta  # wanted charging power (might be -ve)

            # with this setup, charging power shouldn't need to go as high as 2kW
            # (that would imply solar of around 7.7kW)
            assert wcp < 25

            if ecp < 0 and delta > 0:
                print("need to reduce discharge")
            elif paused and wcp > 0:
                requests.append(commands.write_named_register('battery_pause_mode', 0))
                paused = False
            elif wcp <= 0 and not paused:
                requests.append(commands.write_named_register('battery_pause_mode', 1))
                paused = True

            if wcp > 0 and ecp >= 0 and cp != wcp and not paused:
                requests.append(commands.write_named_register('battery_charge_limit', wcp))

            if delta > 0:
                # generation should fall - hack the moving averages.
                # If things still look bad, they'll pop back up again quite quickly
                gma -= delta * 100
                gdecay -= delta * 100

            # print(requests)
            elapsed = 0

        if len(requests) > 0:
            client.execute(requests, timeout=2.0, retries=1, return_exceptions = True)

        await asyncio.sleep(delay)
        elapsed += delay  # only needs to be approx

if __name__ == "__main__":

    now = datetime.now()
    tstamp = now.strftime("%Y%m%d-%H%M")

    # log to both file and console
    file_log_handler = logging.FileHandler("/tmp/monitor." + tstamp + ".log")
    _logger.addHandler(file_log_handler)

    stderr_log_handler = logging.StreamHandler()
    _logger.addHandler(stderr_log_handler)

    # nice output format
    formatter = logging.Formatter(fmt="%(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_log_handler.setFormatter(formatter)

    _logger.setLevel(logging.INFO)

    zf = GzipFile(filename="/tmp/capture." + tstamp + ".gz", mode="wb")
    asyncio.run(monitor(zf))
