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

from RPi import GPIO
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

    def __init__(self, controller):
        self.controller = controller
        self.state = None
        self.op = None
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
        self.setup()
        self.reset_state()

    def setup(self):
        GPIO.setmode(GPIO.BCM)
        for pin in outputs.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, False)

        for (name, pin) in inputs.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)        
            
            GPIO.add_event_detect(pin, GPIO.BOTH, 
                                  self._debounce(0.01,self._ifhigh(getattr(self,name))), 100)

    def cleanup(self):
        """Call on unload so that the raspberry pi releases its gpio pins"""
        GPIO.cleanup()
        for pin in inputs.values():
            GPIO.remove_event_detect(pin)

    def _debounce(self,delay, cb):
        """ Empirically determined that we need a delay to be able to read
            the value of an input after an edge trigger. This returns a delay
            function which then calls the callback """

        def fn(*args, **kwargs):
            time.sleep(delay)
            dbg("debounce %s" %args)
            return cb(*args, **kwargs)
        return fn

    def _ifhigh(self, cb):
        """ Calls the callback is the input pin is high """
        def fn(pin, *args, **kwargs):
            dbg("ifhigh %s "% (pin))
            if GPIO.input(pin):
                dbg("calling callback")
                return cb(pin, *args, **kwargs)
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

    def dispatch(self, event, *args):
        """ Calls the appropriate operation for the current state and event """
        dbg( "dispatch event: %s " % event)
        self.op = callable(self.map.get(self.state).get(event, False)) and event
        self.map.get(self.state).get(event, self.noop)(*args)
    
    def permit(self, event):
        """ Is the event allowable in this state """
        return callable(self.map.get(self.state).get(event, None))
        
    #
    # Input Callbacks
    #
    def upper(self, pin):
        """ Upper limit switch callback """
        self.dispatch(UPPER)

    def lower(self, pin):
        """ Lower limit switch callback """
        self.dispatch(LOWER)

    def up(self, pin):
        """ Up direction command switch """
        # undone -- should the other edge for up stop?
        self.dispatch(UP)

    def down(self, pin):
        """ Down direction command switch """
        self.dispatch(DOWN)

    #
    # Operations
    #
    def open(self):
        """ initiates opening the door """
        if self.permit(UP):
            dbg('Opening')
            self._direction(UP)
            self._power(ON)
            self.state = OPENING

    def close(self):
        """ initiates closing the door """
        if self.permit(DOWN):
            dbg('Closing')
            self._direction(DOWN)
            self._power(ON)
            self.state = CLOSING

    def stop(self): 
        """ Stops the current operations, shuts down power to the outputs. """
        dbg ('stopping')
        self._power(OFF)
        self._direction(OFF)
        self.reset_state()

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
        stat = {'state': self.state,
                'operation': self.op}
        for name,pin in inputs.items():
            stat[name] = GPIO.input(pin)
        return json.dumps(stat)



