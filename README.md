This program reads current temperature and humidity measurements from a Misol HP3001 system and publishes them to an MQTT broker.

This package requires Python 3.

Only a single HP3001 device may be connected to the computer.

A udev rules file is included to grant the `plugdev` group access to the device.  The user running this program should be a member of `plugdev`, or the rules file should be modified to allow that user access.  This program does not need to run as root.

Prerequisites:
* pyhidapi

Installation:

    pip install hid paho-mqtt
    sudo cp hp3001.rules /etc/udev/rules.d/

