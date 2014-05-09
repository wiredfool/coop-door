Coop Door Controller
=========

or, using the Raspberry pi GPIO to control custom power electronics


Take 2: RPIO 
====== 

RPIO seems to be the way forward, except that I have to manage my own
tcp socket for communication with the frontend.

Take 1: Dbus
======

See the dbus branch.


Interface
=====

Your standard Basic ugly interface, but with websockets and svg. 

Websocket communication through flask-sockets is used for status
updates, Those updates are filtered through SVG for a rough display of
the state of the door and the switches. 