'''
Translate TROPESS retrievals to xtralite
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

RECDIM = 'nsound'

def tropess(fin, ftr):
    '''Translate TROPESS retrievals to xtralite'''
#   1. Flatten groups and rename dimensions and variables
    pout = call(['ncks', '-O', '-G', ':', fin, ftr])
    pout = call(['ncrename', '-d', 'target,'+RECDIM, ftr])
    pout = call(['ncrename', '-d', 'level,navg', ftr])
    pout = call(['ncrename', '-v', 'time,time_offset', ftr])
    pout = call(['ncrename', '-v', 'latitude,lat', ftr])
    pout = call(['ncrename', '-v', 'longitude,lon', ftr])
    pout = call(['ncrename', '-v', 'x,obs', ftr])
    pout = call(['ncrename', '-v', 'xa,priorpro', ftr])

#   2. Replace averaging kernel with product of it and pwf
    ncf = netCDF4.Dataset(ftr, 'a') 

    pbotin = ncf.variables['pressure'][:]
    peavgs = np.append(pbotin, np.zeros((pbotin[:,0].size,1)), 1)
    dpavgs = peavgs[:,:-1] - peavgs[:,1:]
    dpavgs.mask = pbotin.mask
    avgkin = ncf.variables['averaging_kernel'][:]
#   still not quite right because of ln and dimensions of avgkin
#   just do a for loop over the damn level variable. there's only 26
    avgker = np.inner(dpavgs.T, avgkin.T).T

#   3. Create total column a priori (priorpro) and uncertainty (uncert)
    pwf = dpavgs / peavgs[:,1]
    pwf.mask = dpavgs.mask

    proa = ncf.variables['priorpro']
    cola = ncf.createVariable('priorobs', 'f4', (RECDIM,))
    cola.units         = 'ppbv'
    cola.long_name     = 'Average column a priori'
    cola.missing_value = np.float32(-999.)
    cola[:] = np.sum(pwf[:]*proa[:], axis=1)

    prou = ncf.variables['uncertainty']
    colu = ncf.createVariable('uncert', 'f4', (RECDIM,))
    colu.units         = 'ppbv'
    colu.long_name     = 'Average column uncertainty'
    colu.missing_value = np.float32(-999.)
    colu[:] = np.sum(pwf[:]*prou[:], axis=1)

#   4. Create sounding_date and sounding_time variables
    dsecs = ncf.variables['time_offset'][:]

    t0    = dtm.datetime(1993, 1, 1)
    dates = ncf.createVariable('date', 'i4', (RECDIM,))
    times = ncf.createVariable('time', 'i4', (RECDIM,))
    for ir in range(len(dsecs)):
        tt = t0 + dtm.timedelta(seconds=dsecs[ir])
        dates[ir] = tt.day    + tt.month*100  + tt.year*10000
        times[ir] = tt.second + tt.minute*100 + tt.hour*10000

    dates.units         = 'MMDDYY'
    dates.long_name     = 'Sounding Date'
    dates.missing_value = np.int32(-999)
    times.units         = 'hhmmss'
    times.long_name     = 'Sounding Time'
    times.missing_value = np.int32(-999)
    times.comment       = 'from scan start time in UTC'

    ncf.close()

    return None
