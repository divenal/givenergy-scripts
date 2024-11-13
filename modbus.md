### Modbus script

During the summer, I want to export as much solar as possible directly. But when power exceeds the 5kW AC limit, I need to divert some to the battery, else I get clipping. There's basically two ways to do this:
 - operate a battery-first policy, and actively manage the max charging power so that just enough goes to the battery to keep AC close to 5kW.
 - operate a grid-first policy, so that the inverter automatically sends excess to the battery.

Unfortunately, option 2 does't seem to be implemented directly. But it turns out that turning off eco mode does have that side effect. But of course it has other desirable side effects, such as losing dynamic discharge to match consumption.

First version of the script used the first approach. I'm now trying the second approach, which should require fewer adjustments. But it still requires closer monitoring of the state than is practical using the API, hence use of a direct connection to the inverter using modbus.

- When solar is low, eco mode is on, and battery-charging is paused
- When solar is high, eco mode is off, and battery-charging is unpaused.

The modbus script is also allowed to force-export when it detects that battery level is relatively high. The rule there is that it's only allowed to do that within the time period defined by discharge-timer-slot#2 (and the pause timer), and it simply turns the timed-export flag on and off as required.

One final job of the script: when I force an export, I tend to do it at less than max power. But when I'm in normal dynamic discharge mode, I want full discharge power to be available. So the script automatically detects when we are not exporting, and sets power to max.

The current, rather ad-hoc, rule, is that during the time window defined by the pause timer, the modbus script is in charge. Otherwise, it limits its activity. (By having the script configured using inverter timers, it saves having to try to send it messages by some other means while it's running. I can communicate to it, rather crudely, through these timers. Though it has since occurred to me that I can use a mmap file to send it data too. So I'll probably add that.)

