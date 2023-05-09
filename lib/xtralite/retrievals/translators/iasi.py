'''
Translate IASI retrievals to xtralite
'''
# Copyright 2022 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
#===============================================================================

import datetime as dtm
import numpy as np
import netCDF4
from subprocess import call

# IASI CH4 to xtralite
#=====================
def translate_ch4(fin, ftr):
    RECDIM = 'nsound'

#   1. Flatten groups, delete sounding_id, and convert to netCDF4; otherwise
#   this is very slow 
    pout = call(['ncks', '-O', '-3', '-C', '-G', ':', '-x', '-v',
        'sounding_id', fin, ftr])

# IASI CO to xtralite
#====================
def translate_co(fin, ftr):
    RECDIM = 'nsound'

#   1. Flatten groups, delete sounding_id, and convert to netCDF4; otherwise
#   this is very slow 
    pout = call(['ncks', '-O', '-3', '-C', '-G', ':', '-x', '-v',
        'sounding_id', fin, ftr])

# Will need to depend on version for co
translate = {
    'ch4': translate_ch4,
    'co':  translate_co}
