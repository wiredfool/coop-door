#!/usr/bin/python

""" Server for the door to run as root (to access the gpio pins with a
defined interface that can be accessed by anything that can control
dbus, like, another python program that's not running as root .

"""

import dbus.service
import door

class remote(dbus.service.Object):
    def __init__(self):
        bus_name=dbus.service.BusName('com.wiredfool.coop', bus=dbus.SystemBus())
        dbus.service.Object.__init__(self, bus_name, object_path='/door')
        self.door = door.door(self)

    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='')
    def open(self):
        return self.door.open()

    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='')
    def close(self):
        return self.door.close()

    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='')
    def stop(self):
        return self.door.stop()
    
    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='s')
    def status(self):
        return self.door.status()

    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='')
    def reload(self):
        self.door.cleanup()
        reload(door)
        self.door = door.door(self)

    @dbus.service.method('com.wiredfool.coop', in_signature='', out_signature='')
    def cleanup(self):
        return self.door.cleanup()

if __name__=='__main__':
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    import gobject
    r = remote()
    try:
        loop = gobject.MainLoop()
        loop.run()
    except Exception, msg:
        print "Exception in main loop: %s" % msg
    finally:
        r.stop()
        r.cleanup()
        loop.quit()

