'''
Translate European GHG retrievals to xtralite
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
from subprocess import check_call

RECDIM = 'nsound'

def euroghg(fin, ftr, var):
    '''Translate European GHG retrievals to xtralite'''

    varlo = var.lower()

#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding_dim,'+RECDIM,
        '-d', 'layer_dim,navg',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'pressure_levels,peavg',
        '-v', 'x'+varlo+',obs',
        '-v', 'x'+varlo+'_uncertainty,uncert',
        '-v', 'x'+varlo+'_averaging_kernel,avgker',
        '-v', 'x'+varlo+'_quality_flag,qcflag',
        '-v', varlo+'_profile_apriori,priorpro',
        '-v', 'pressure_weight,pwf', ftr, ftr])

#   3. Create date and time variables
    ncf = netCDF4.Dataset(ftr, 'a') 

    dsecs = ncf.variables['time_offset'][:]
    t0    = dtm.datetime(1970,1,1)
    dates = ncf.createVariable('date', 'i4', (RECDIM,))
    times = ncf.createVariable('time', 'i4', (RECDIM,))
    for ir in range(len(dsecs)):
        tt = t0 + dtm.timedelta(seconds=dsecs[ir])
        dates[ir] = tt.day    + tt.month*100  + tt.year*10000
        times[ir] = tt.second + tt.minute*100 + tt.hour*10000

    dates.units     = 'MMDDYY'
    dates.long_name = 'Sounding Date'
    times.units     = 'hhmmss'
    times.long_name = 'Sounding Time'
    times.comment   = 'from scan start time in UTC'

#   4. Replace averaging kernel with product of it and pwf
    pwf    = ncf.variables['pwf']
    avgker = ncf.variables['avgker']
    avgker[:] = avgker[:]*pwf[:]

#   5. Create prior column variable (priorobs)
    apro = ncf.variables['priorpro']
    acol = ncf.createVariable('priorobs', 'f4', (RECDIM,))
    acol.units     = apro.units
    acol.long_name = 'A priori X' + var.upper() + ' Value'
    acol[:] = np.sum(pwf[:]*apro[:], axis=1)

    ncf.close()

    return None
