# World's Greatest Oven (Appliance?) Thermometer
# Overview
This is a standalone Raspberry Pi hardware assembly project and associated software that can be used to measure, chart and record appliance temperatures over time, using a cable-attached thermocouple probe.
# Features
On the the 2.8" PiTFT capacitive touchscreen, this device will show the current temperature, with the option of an additional save/hold temperature value or even a graph of the temperature over time.
The selections are chosen by pressing associated buttons on the PiTFT screen's board and by touching the PiTFT screen.

You can also reset the timer, in case you want to start recording again – say after a false start or changing adjustment values.

It also creates a csv log file that can later be used offline, to build fancy graphs or spreadsheets for analysis purposes.

Optionally, this Linux-based device can be shutdown and/or restarted at the touch of a single button, to avoid having to remove and replace the power supply connection.

There is also a handy flashing LED activity indicator, so that you can check if the software is alive: especially useful in "headless" mode.

No Internet connection is required, because all of the timing is relative and typical CPU utilization is less than 10%.

For development purposes, the software can be tested on an attached X11 HDMI screen/keyboard (or via VNC) without access to the PiTFT itself, by un-commenting a single Python statement, though you definitely need the Perma-Proto Hat board with the MAX31855 board attached.
# Changes
Proto22 is the first beta version.

Proto25 includes the following changes.
- Fix the problem of the activity LED being left on after the programme exits
- Save the last two csv log files when the programme is restarted 
- Change the chart line's colour from red to blue if the current temperature is at or below freezing
# Usage
Follow the instructions in the documentation to build the hardware and to install pre-requisite software.
The following command will execute the programme.

sudo python Proto25.py

or

sudo python3 Proto25.py
# Known Bugs
The activity LED may stay on after the software exits. (Proto22 - 2019-02-24)

The csv log does not include time-zero values at startup or after reset. (Proto25 - 2019-03-08)
