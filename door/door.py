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
      Error: power is on, dpdt is set to down, and the upper 
        limit switch has had an open/closed transition. Power
        should be immediately turned off and requires manual 
        intervention. 

   There are 3 operations:
      Up: opens the door.
      Down: closes the door.
      Stop: Stops the current operation. 
      
"""

import RPIO as GPIO
import time
import json

import syslog

def dbg(s):
    #print s
    syslog.syslog(s)

# States
OPEN, CLOSED, OPENING, CLOSING, STOPPED, ERROR = 'open', 'closed', 'opening', 'closing', 'stopped', 'error'
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

    def __init__(self, controller, thread=True, port=None):
        self.controller = controller
        self.state = None
        self.thread = thread
        self.port = port
        self.out_state = dict((k,False) for k in outputs)
        
        """ state: {Event:op} """
        self.map = { OPEN: { DOWN: self.close, } ,
                     CLOSING: { LOWER: self.stop, 
                                UPPER: self.error,
                                UP: self.open,  },
                     CLOSED: { UP: self.open, },
                     OPENING: { UPPER: self.stop,
                                DOWN: self.close, },
                     STOPPED: { UP: self.open, 
                                DOWN: self.close, },
                     ERROR: { UP: self.open, 
                              DOWN: self.close, },
                     None: {}
                     }

        self.commands = {
            'open': self.open,
            'close': self.close,
            'stop': self.stop,
            'status': self.status,
            }
        
        self.setup()
        self.reset_state()
        if self.thread:
            self.run()

    def setup(self):
        GPIO.setmode(GPIO.BCM)
        for pin in outputs.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

        for (name, pin) in inputs.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)        
            
            GPIO.add_interrupt_callback(pin,
                                        getattr(self,name),
                                        edge='rising',
                                        debounce_timeout_ms=100)
        if self.port:
            GPIO.add_tcp_callback(self.port, self.command_dispatch)

    def run(self):
        GPIO.wait_for_interrupts(threaded=self.thread)
        
    def cleanup(self):
        """Call on unload so that the raspberry pi releases its gpio pins"""
        GPIO.cleanup()
        for pin in inputs.values():
            GPIO.del_interrupt_callback(pin)
        RPIO.stop_waiting_for_interrupts()

    def _debounce(self,delay, cb):
        """ Empirically determined that we need a delay to be able to read
            the value of an input after an edge trigger. This returns a delay
            function which then calls the callback """

        def fn(*args, **kwargs):
            dbg("debounce %s" %args)
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

    def command_dispatch(self, socket, msg):
        """ calls the appropriate command """
        msg = msg.strip().lower()
        ret = self.commands.get(msg, self.noop)()
        dbg('command dispatch: %s -> %s' %(msg,ret))
        if ret == None: return socket.send('Unknown\n')
        if ret == True: return socket.send('Ok\n')
        if ret == False: return socket.send('Incorrect State\n')
        if ret: return socket.send(ret+'\n')
    
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
    def open(self):
        """ initiates opening the door """
        dbg('command: open')
        if self.permit(UP):
            dbg('Opening')
            self._direction(UP)
            self._power(ON)
            self.state = OPENING
            return True
        return False

    def close(self):
        """ initiates closing the door """
        dbg('command: close')
        if self.permit(DOWN):
            dbg('Closing')
            self._direction(DOWN)
            self._power(ON)
            self.state = CLOSING
            return True
        return False

    def stop(self): 
        """ Stops the current operations, shuts down power to the outputs. """
        dbg ('stopping')
        self._power(OFF)
        self._direction(OFF)
        self.reset_state()
        return True

    def error(self):
        dbg('ERROR, turning it off')
        self._power(OFF)
        self._direction(OFF)
        self.state = ERROR

    #
    # Power Control Functions
    # 
    def _power(self, val):
        """ Control the power to the mosfet, true=on/false=off"""
        dbg("setting power %s"%val)
        GPIO.output(outputs['power'], val)
        
    def _direction(self, val):
        """ set the direction relay """
        dbg('setting direction %s, %s' %(val, val == UP))
        GPIO.output(outputs['direction'],  val == UP)
            
    #
    # Reporting
    # 

    def status(self):
        stat = {'state': self.state}
        for name,pin in inputs.items():
            stat[name] = GPIO.input(pin)
        return json.dumps(stat)


if __name__=='__main__':
    d = door(None, False, 8953)
    d.run()
