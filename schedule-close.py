#!/usr/bin/python

# Schedule the door to close at the end of civil twilight, using the astral library. 


import os, sys
from astral import Astral

city_name = 'Seattle'

astral = Astral()
astral.solar_depression = 'civil'

city = astral[city_name]

sun = city.sun(local=True)

cmd = """echo '%s %s' | at %s""" % (sys.executable, 
                                    os.path.abspath(os.path.join(os.path.dirname(__file__), 'door/close.py')), 
                                    sun['dusk'].strftime("%H:%M"))
         
print cmd
os.system(cmd)
