"""
   Door controller for a chicken coop

   This is hooked to a power screwdriver and battery system through
   the gpio port. The screwdriver is connected to a vertical sliding
   door through a string and pulley arrangement. Turning the motor one
   way raises the door, the other way lowers it. However, if all the
   string is let out, and the motor continues to run, it will start
   winding the string back up and will eventually cause the door to
   raise back up and jam. We will work around this mechanical bug in
   software.


   Inputs:
      Two sensors: an upper and a lower limit switch.
      Two switches: manual up and down switches. (dpdt momentary, likely)

   Outputs:
      Power: a mosfet, likely will be run on the PWM
         pin for speed control
      Direction: a dpdt relay. On will be one direction, 
         off the other.  

   There are N states:
      Open: upper limit switch is closed, power is off
      Closed: lower limit switch is closed, power is off
      Opening: power is on, dpdt relay is set to up
      Closing: power is on, dpdt relay is set to down 
      Stopped: Neither limit switch is closed, power is off
      Error: Door has jammed open when attempting to close.

   There are 3 operations:
      Up: opens the door.
      Down: closes the door.
      Stop: Stops the current operation. 
      Error: power was on, door is closing, and the upper 
        limit switch has closed. Power should be immediately
        turned off.
"""

import RPIO as GPIO

# restrict to localhost.
from RPIO import _RPIO
_RPIO._TCP_SOCKET_HOST = '127.0.0.1'

import time
import json

import syslog

def dbg(s):
    #print s
    syslog.syslog(s)

# States
OPEN, CLOSED, OPENING, CLOSING, STOPPED, ERROR, DEAD, ERROR_RECOVERY = \
    'open', 'closed', 'opening', 'closing', 'stopped', 'error', 'dead', 'error_recovery'
# Events
UP, DOWN, UPPER, LOWER = 'up', 'down', 'upper', 'lower' 
# Power Control
ON, OFF = True, False

outputs = {
    'power':24,
    'direction':23,
    }

inputs = {
    'upper':22,
    'lower': 18,
    'up': 25,
    'down': 17,
}


class door(object):
    """ state machine to control the door """

    def __init__(self, controller, use_thread=True, port=None):
        self.controller = controller
        self.state = None
        self.use_thread = use_thread
        self.port = port
        self.out_state = dict((k,False) for k in outputs)

        self.status_sockets = set()
        
        """ state: {Event:op} """
        self.map = { OPEN:    { DOWN:  self.close,     },
                     CLOSING: { LOWER: self.stop, 
                                UPPER: self.error,
                                UP:    self.stop,      },
                     CLOSED:  { UP:    self.open,      },
                     OPENING: { UPPER: self.stop,
                                DOWN:  self.stop,      },
                     STOPPED: { UP:    self.open, 
                                DOWN:  self.close,     },
                     ERROR:   { DOWN:  self.err_close,
                                LOWER: self.stop,
                                UPPER: self.stop,      },
                     ERROR_RECOVERY: {
                                LOWER: self.stop,
                                UPPER: self.stop,      },
                     DEAD:    {},                     
                     None:    {}
                     }

        self.commands = {
            'open': self.open,
            'close': self.close,
            'stop': self.stop,
            'status': self.status,
            'enroll': self.enroll,
            }
        
        self.setup()
        self.reset_state()
        if self.use_thread:
            self.run()

    def setup(self):
        GPIO.setmode(GPIO.BCM)
        for pin in outputs.values():
            GPIO.setup(pin, GPIO.OUT)
            
        self._power(False)
        self._direction(False)

        for (name, pin) in inputs.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)        
            
            GPIO.add_interrupt_callback(pin,
                                        self._delay(0.05,
                                                    self._ifhigh(getattr(self,name))),
                                        edge='both',
                                        debounce_timeout_ms=100)
        if self.port:
            GPIO.add_tcp_callback(self.port, self.command_dispatch)

    def run(self):
        while True:
            try:
                GPIO.wait_for_interrupts(threaded=self.use_thread)
            except IOError:
                # interrupted system call
                pass
            except KeyboardInterrupt:
                #ctrl-c
                break
        
    def cleanup(self):
        """Call on unload so that the raspberry pi releases its gpio pins"""
        GPIO.cleanup()
        for pin in inputs.values():
            GPIO.del_interrupt_callback(pin)
        GPIO.stop_waiting_for_interrupts()

    def _delay(self,delay, cb):
        """ Empirically determined that we need a delay to be able to read
            the value of an input after an edge trigger. This returns a delay
            function which then calls the callback """

        def fn(*args, **kwargs):
            dbg("delay %s" % str(args))
            time.sleep(delay)
            return cb(*args, **kwargs)
        return fn

    def _ifhigh(self, cb):
        """ Calls the callback is the input pin is high """
        def fn(pin, *args, **kwargs):
            dbg("ifhigh %s "% (pin))
            if GPIO.input(pin):
                dbg("pin %s high, calling callback" %pin)
                return cb(pin, *args, **kwargs)
            dbg("pin %s low, not calling" %pin)
            self.notify_enrolled(self.status())
        return fn

    def reset_state(self):
        """ Determines the proper state when the motor is stopped"""
        if GPIO.input(inputs['upper']):
            self.state = OPEN
        elif GPIO.input(inputs['lower']):
            self.state = CLOSED
        else: 
            self.state = STOPPED
            
    def noop(self, *args, **kwargs):
        """ a dummy function"""
        # can't be a lambda because of the function signature
        pass

    def event_dispatch(self, event, *args):
        """ Calls the appropriate operation for the current state and event """
        dbg( "event dispatch: %s " % event)
        self.map.get(self.state).get(event, self.noop)(*args)
        self.notify_enrolled(self.status())
        
    def notify_enrolled(self, status):
        """ Notifies all of the listening status connections of the
        current status of the system."""

        # Undone -- delegate this to a different thread.
        # this is not realtime priority, and I don't want to
        # delay any of the gpio events
        err = []
        dbg('Updating %d sockets with status' % len(self.status_sockets))
        for sock in self.status_sockets:
            try:
                sock.sendall("Status\n"+status)
            except:
                dbg('Error sending to socket: removing')
                err.append(sock)
                
        [self.status_sockets.remove(sock) for sock in err]

    def command_dispatch(self, socket, msg):
        """ calls the appropriate command """
        msg = msg.strip().lower()
        ret = self.commands.get(msg, self.noop)(**{'socket':socket})
        dbg('command dispatch: %s -> %s' %(msg,ret))
        if ret == None: return self.response(socket, 'Error')
        if ret == True: return self.response(socket, 'Ok') 
        if ret == False: return self.response(socket, 'Incorrect State')
        if ret: return socket.send("Status\n"+ret+'\n')

    def response(self, socket, msg):
        status = self.status()
        try:
            socket.sendall(msg + '\n' + self.status() + '\n')
        except Exception, msg:
            # error sending to the socket,
            dbg.log("Exception sending response: %s"%msg)
            socket.setblocking(0)
            
        self.notify_enrolled(status)
    
    def permit(self, event):
        """ Is the event allowable in this state """
        return callable(self.map.get(self.state).get(event, None))
        
    #
    # Input Callbacks
    #
    def upper(self, pin, val=None):
        """ Upper limit switch callback """
        self.event_dispatch(UPPER)

    def lower(self, pin, val=None):
        """ Lower limit switch callback """
        self.event_dispatch(LOWER)

    def up(self, pin, val=None):
        """ Up direction command switch """
        # undone -- should the other edge for up stop?
        self.event_dispatch(UP)

    def down(self, pin, val=None):
        """ Down direction command switch """
        self.event_dispatch(DOWN)

    #
    # Operations
    #
    def open(self, *args, **kwargs):
        """ initiates opening the door """
        dbg('command: open')
        if self.permit(UP):
            dbg('Opening')
            self._direction(UP)
            self._power(ON)
            self.state = OPENING
            return True
        return False

    def close(self, *args, **kwargs):
        """ initiates closing the door """
        dbg('command: close')
        if self.permit(DOWN):
            dbg('Closing')
            self._direction(DOWN)
            self._power(ON)
            self.state = CLOSING
            return True
        return False

    def stop(self, *args, **kwargs): 
        """ Stops the current operations, shuts down power to the outputs. """
        dbg ('stopping')
        self._power(OFF)
        self._direction(OFF)
        self.reset_state()
        return True

    def error(self, *args, **kwargs):
        dbg('ERROR, turning it off')
        self._power(OFF)
        self._direction(OFF)
        self.state = ERROR

    def err_close(self, *args, **kwargs):
        dbg('Err State, attempting to close')
        if self.state == ERROR:
            self._state = ERROR_RECOVERY
            self._direction(UP)
            self._power(ON)
            time.sleep(0.25)
            self._power(OFF)
            if GPIO.input(inputs['upper']):
                # still jammed. We're dead
                dbg('Still jammed, dying')
                self._direction(OFF)
                self.state = DEAD
                return False
            else:
                # Unjammed. give it a shot. Any switch will stop.
                dbg('Unjammed, continuing to close by opening')
                self.power(ON)
                return True
        return False

    #
    # Reporting command
    #
    def enroll(self, socket=None,*args, **kwargs):
        "Adds the socket to the status broadcasts"
        dbg('Enrolling a socket: %s' %socket)
        if socket is not None:
            self.status_sockets.add(socket)
            socket.setblocking(0)
            return True
        return False
    #
    # Power Control Functions
    # 
    def _power(self, val):
        """ Control the power to the mosfet, true=on/false=off"""
        dbg("setting power %s"%val)
        GPIO.output(outputs['power'], not val)
        
    def _direction(self, val):
        """ set the direction relay """
        dbg('setting direction %s, %s' %(val, val == UP))
        GPIO.output(outputs['direction'],  val == UP)
            
    #
    # Reporting
    # 

    def status(self, *args, **kwargs):
        stat = {'state': self.state}
        for name,pin in inputs.items():
            stat[name] = GPIO.input(pin)
        return json.dumps(stat)


if __name__=='__main__':
    d = door(None, False, 8953)
    d.run()
    d.cleanup()
