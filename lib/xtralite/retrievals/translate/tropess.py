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
import xarray as xr
import netCDF4
from subprocess import check_call

RECDIM = 'nsound'
FILLSING = np.float32(-999.)
FILLINT  = np.int32(-999)
OBSUNITS = 'mol mol-1'

def translate(fin, ftr):
    '''Translate TROPESS retrievals to xtralite'''
    ftmp = ftr + '.tmp'

#   1. Flatten (and remove) groups
    pout = check_call(['ncks', '-O', '-x', '-g', 'geolocation',
        '-G', ':', fin, ftmp])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'target,'+RECDIM,
        '-d', 'level,navg',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'xa,priorpro', ftmp, ftmp])

    ncf = netCDF4.Dataset(ftmp, 'a') 

#   Assume pressures are bottoms and top is zero
    pbotin = ncf.variables['pressure'][:]
    numsnd = pbotin[:].shape[0]
    numavg = pbotin[:].shape[1]

#   3. Create pressure edges of averaging kernel (peavg)
    nedge = ncf.createDimension('nedge', numavg+1)
    peavg = ncf.createVariable('peavg', 'float32', (RECDIM,'nedge'),
        fill_value=FILLSING)
    peavg.units = 'hPa'
    peavg.long_name = 'Edge pressures of averaging kernel'
    peavg.missing_value = FILLSING
    peavg[:] = np.append(pbotin, np.zeros((numsnd,1)), 1)

    dpavg = peavg[:,:-1] - peavg[:,1:]
    dpavg.mask = pbotin.mask

#   4. Create column averaging kernel (avgker)
    avgkin = ncf.variables['averaging_kernel'][:]
    avgker = ncf.createVariable('avgker', 'float32', (RECDIM,'navg'),
        fill_value=FILLSING)
    avgker.units = OBSUNITS + ' / ' + OBSUNITS
    avgker.long_name = 'Averaging kernel'
    avgker.missing_value = FILLSING
    avgker[:] = np.zeros_like(dpavg)

    pwf = np.zeros_like(dpavg)
    for kk in range(numavg):
        pwf[:,kk] = dpavg[:,kk] / np.sum(dpavg, axis=1)
        avgker[:] = avgker[:] + dpavg*avgkin[:,:,kk]
    pwf.mask = dpavg.mask
    avgker[:].mask = dpavg.mask

#   Check averaging kernel transpose
#   Still need to account for log space

#   5. Create column obs (obs), a priori (priorpro), and
#   uncertainty (uncert)
    obspro = ncf.variables['x']
    obs = ncf.createVariable('obs', 'float32', (RECDIM,),
        fill_value=FILLSING)
    obs.units = OBSUNITS
    obs.long_name = 'Average column observation'
    obs.missing_value = FILLSING
    obs[:] = np.sum(pwf[:]*obspro[:], axis=1)

    priorpro = ncf.variables['priorpro']
    priorobs = ncf.createVariable('priorobs', 'float32', (RECDIM,),
        fill_value=FILLSING)
    priorobs.units = OBSUNITS
    priorobs.long_name = 'Average column a priori'
    priorobs.missing_value = FILLSING
    priorobs[:] = np.sum(pwf[:]*priorpro[:], axis=1)

    uncpro = ncf.variables['observation_error']
    uncert = ncf.createVariable('uncert', 'float32', (RECDIM,),
        fill_value=FILLSING)
    uncert.units = OBSUNITS
    uncert.long_name = 'Average column uncertainty'
    uncert.missing_value = FILLSING
    uncert[:] = 0.
    for kk in range(numavg):
        uncert[:] = uncert[:] + np.sum(dpavg*uncpro[:,:,kk], axis=1)

#   6. Create sounding_date and sounding_time variables
#   Could change to datetime_utc
    dvecs = ncf.variables['datetime_utc'][:]
    dates = ncf.createVariable('date', 'int32', (RECDIM,), fill_value=FILLINT)
    times = ncf.createVariable('time', 'int32', (RECDIM,), fill_value=FILLINT)

    dates.units = 'yyyymmdd'
    times.units = 'HHMMSS'
    dates.long_name = 'Sounding date'
    times.long_name = 'Sounding time'
    dates.missing_value = FILLINT
    times.missing_value = FILLINT

    dates[:] = dvecs[:,0]*10000 + dvecs[:,1]*100 + dvecs[:,2]
    times[:] = dvecs[:,3]*10000 + dvecs[:,4]*100 + dvecs[:,5]

    ncf.close()

#   7. Delete extra variables and convert back to netCDF4
    pout = check_call(['ncks', '-O', '-x', '-v', 'datetime_utc,' +
        'time_offset,year_fraction,average_cloud_eod,cloud_top_pressure,' +
        'pressure,altitude,air_density,surface_temperature,signal_dof,' +
        'averaging_kernel,observation_error,x_test,x_raw,x', ftmp, ftmp])

#   8. Sort
    ds = xr.open_dataset(ftmp, mask_and_scale=False)
    ds = ds.sortby('time')
    ds.to_netcdf(ftr)
    ds.close()

    pout = check_call(['rm', ftmp])

#   Land flag is really an int64?

    return None
