

import dbus
sys_bus = dbus.SystemBus()
raw_server = sys_bus.get_object('com.wiredfool.coop', '/door')
print raw_server

server = dbus.Interface(raw_server, 'com.wiredfool.coop')
print server.status()


