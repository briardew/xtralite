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

def translate(fin, ftr, var):
    '''Translate European GHG retrievals to xtralite'''

    import subprocess

    varlo = var.lower()

#   1. Flatten groups, convert to netCDF3
#   Need netCDF3 conversion to avoid ncrename bug on some systems
    pout = check_call(['ncks', '-O', '-3', '-G', ':', fin, ftr])

#   Account for difference in nedge
#   BESD uses level_dim = nedge = navg + 1, UOL uses nedge = navg
    try:
        pout = check_call(['ncrename', '-O',
            '-d', 'sounding_dim,'+RECDIM,
            '-d', 'layer_dim,navg',
            '-d', 'level_dim,nedge', ftr, ftr],
            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        pout = check_call(['ncrename', '-O',
            '-d', 'n,'+RECDIM,
            '-d', 'm,navg', ftr, ftr])

        ncf = netCDF4.Dataset(ftr, 'a') 
        navg  = ncf.dimensions['navg']
        nedge = ncf.createDimension('nedge', navg.size)
        ncf.close()

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
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

#   3. Create date, time, and sounding variables
    ncf = netCDF4.Dataset(ftr, 'a') 

    dates = ncf.createVariable('date', 'i4', (RECDIM,))
    times = ncf.createVariable('time', 'i4', (RECDIM,))
    secs = ncf.variables['time_offset'][:]
    for nn in range(len(secs)):
        tt = dtm.datetime(1970,1,1) + dtm.timedelta(seconds=secs[nn])
        dates[nn] = tt.day    + tt.month*100  + tt.year*10000
        times[nn] = tt.second + tt.minute*100 + tt.hour*10000

    dates.units = 'yyyymmdd'
    times.units = 'HHMMSS'
    dates.long_name = 'Sounding date'
    times.long_name = 'Sounding time'

#   4. Replace averaging kernel with product of it and pwf
    pwf    = ncf.variables['pwf']
    avgker = ncf.variables['avgker']
    avgker[:] = avgker[:]*pwf[:]

#   5. Create prior column variable (priorobs)
    apro = ncf.variables['priorpro']
    acol = ncf.createVariable('priorobs', 'f4', (RECDIM,))
    acol.units = apro.units
    acol.long_name = 'A priori X' + var.upper() + ' Value'
    acol[:] = np.sum(pwf[:]*apro[:], axis=1)

    ncf.close()

    return None
