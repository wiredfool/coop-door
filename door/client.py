"""

Client side interface to the dbus connection to the coop door

"""


import dbus
sys_bus = dbus.SystemBus()

# This is in a module so that we're not making multiple
# copies/versions of this when we run it under web.py

raw_server = sys_bus.get_object('com.wiredfool.coop', '/door')
server = dbus.Interface(raw_server, 'com.wiredfool.coop')

def status():
    return server.status()
def open():
    return server.open()
def close():
    return server.close()
def stop():
    return server.stop()

