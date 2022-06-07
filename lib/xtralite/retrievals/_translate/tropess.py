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
from subprocess import check_call

RECDIM = 'nsound'

def translate(fin, ftr):
    '''Translate TROPESS retrievals to xtralite'''
#   1. Flatten groups
#   Need -5 so rename doesn't mangle coordiates, converted back below
    pout = check_call(['ncks', '-O', '-x', '-g', 'geolocation', fin, ftr])
    pout = check_call(['ncks', '-O', '-5', '-G', ':', ftr, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'target,'+RECDIM,
        '-d', 'level,navg',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'xa,priorpro',
        '-v', 'x,obs', ftr, ftr])

    ncf = netCDF4.Dataset(ftr, 'a') 

#   Assume pressures are bottoms and top is zero
    pbotin = ncf.variables['pressure'][:]
    nsound = pbotin[:].shape[0]
    navg   = pbotin[:].shape[1]

#   3. Create pressure edges of averaging kernel (peavg)
    nedge = ncf.createDimension('nedge', navg + 1)
    peavg = ncf.createVariable('peavg', 'f4', (RECDIM,'nedge'))
    peavg[:] = np.append(pbotin, np.zeros((nsound,1)), 1)
    dpavg = peavg[:,:-1] - peavg[:,1:]
    dpavg.mask = pbotin.mask

#   4. Create column averaging kernel (avgker)
    avgkin = ncf.variables['averaging_kernel'][:]
    avgker = ncf.createVariable('avgker', 'f4', (RECDIM,'navg'))
    avgker[:] = np.zeros_like(dpavg)
    pwf = np.zeros_like(dpavg)
    for kk in range(navg):
        pwf[:,kk] = dpavg[:,kk] / peavg[:,0]
        avgker[:] = avgker[:] + dpavg*avgkin[:,:,kk]
    pwf.mask = dpavg.mask
    avgker[:].mask = dpavg.mask

#   Check transpose
#   Still need to account for log space

#   5. Create column a priori (priorpro) and uncertainty (uncert)
    proa = ncf.variables['priorpro']
    cola = ncf.createVariable('priorobs', 'f4', (RECDIM,))
    cola.units = 'ppbv'
    cola.long_name = 'Average column a priori'
    cola.missing_value = np.float32(-999.)
    cola[:] = np.sum(pwf[:]*proa[:], axis=1)

    prou = ncf.variables['observation_error']
    colu = ncf.createVariable('uncert', 'f4', (RECDIM,))
    colu.units = 'ppbv'
    colu.long_name = 'Average column uncertainty'
    colu.missing_value = np.float32(-999.)
    colu[:] = 0.
    for kk in range(navg):
        colu[:] = colu[:] + np.sum(dpavg*prou[:,:,kk], axis=1)

#   6. Create sounding_date and sounding_time variables
#   Could change to datetime_utc
    dsecs = ncf.variables['time_offset'][:]

    t0    = dtm.datetime(1993, 1, 1)
    dates = ncf.createVariable('date', 'i4', (RECDIM,))
    times = ncf.createVariable('time', 'i4', (RECDIM,))
    for ir in range(len(dsecs)):
        tt = t0 + dtm.timedelta(seconds=dsecs[ir])
        dates[ir] = tt.day    + tt.month*100  + tt.year*10000
        times[ir] = tt.second + tt.minute*100 + tt.hour*10000

    dates.units = 'MMDDYY'
    dates.long_name = 'Sounding Date'
    times.units = 'hhmmss'
    times.long_name = 'Sounding Time'

    ncf.close()

#   7. Delete extra variables and convert back to netCDF4
    pout = check_call(['ncks', '-O', '-4', '-x', '-v', 'datetime_utc,' +
        'time_offset,year_fraction,target_id,average_cloud_eod,' +
        'cloud_top_pressure,pressure,altitude,air_density,' +
        'surface_temperature,signal_dof,averaging_kernel,' +
        'observation_error,x_test,x_raw', ftr, ftr])

#   Land flag is really an int64?

    return None
