Coop Door Controller
=========

or, using the Raspberry pi GPIO to control custom power electronics


Take 1: Dbus
-----

Use dbus to connect between the unpriveledged web.py webapp front end
and the internal door state machine. Unfortunately it appears that the
gpio thread that recieves edge detect events conflicts with the gevent
loop for the dbus reciever. 

To Install:
```
sudo ln -s coop-dbus.conf /etc/dbus-1/system.d/
sudo ln -s com.wiredfool.coop.service /usr/share/dbus-1/system-services/
```
