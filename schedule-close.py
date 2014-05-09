#!/usr/bin/python

import os
from astral import Astral

city_name = 'Seattle'

astral = Astral()
astral.solar_depression = 'civil'

city = astral[city_name]

sun = city.sun(local=True)
#print('Dusk:    %s' % sun['dusk'].strftime("%H:%M"))

os.system("""echo '/usr/bin/python %s' | at %s""" % 
          (os.path.abspath('door/close.py'), sun['dusk'].strftime("%H:%M")))
