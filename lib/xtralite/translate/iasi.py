'''
Translate IASI retrievals to CoDAS format
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
# * Check we're summing along correct indices
#===============================================================================

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

def translate_co(fin, ftr):
    '''Translate IASI column CO retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = dd.rename({'time':'nsound', 'nlayers':'navg',
        'latitude':'lat', 'longitude':'lon', 'retrieval_quality_flag':'isbad',
        'CO_total_column':'obs', 'CO_total_column_error':'uncert',
        'CO_apriori_partial_column_profile':'priorpro'})

    # Hack to deal with renaming unlimited dimension
    # (files w/o unlimited dims are smaller)
    del dd.encoding['unlimited_dims']

    # Assign date and time variables
    nsound = dd.sizes['nsound']
    secs = dd.get('AERIStime', dd['nsound'])
    days = secs.values[:]/(60.*60.*24.)

    ## Can this be vectorized easily?
    date = np.zeros(nsound, dtype=np.int32)
    time = np.zeros(nsound, dtype=np.int32)
    for nn in range(nsound):
        tt = datetime(2007, 1, 1) + timedelta(days[nn])
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    dd = dd.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date'}))
    dd = dd.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding time'}))

    # Redefine nsound to sounding number in day
    # NB: This needs to come after secs is read
    dd = dd.assign_coords(nsound=np.arange(nsound, dtype=np.int32))

    # Convert uncertainty to absolute from relative
    dd['uncert'].values = dd['uncert'].values * dd['obs'].values
    del dd['uncert'].attrs['comment']

    # Convert quality flag
    dd['isbad'].values = dd['isbad'].values < 2
    dd['isbad'].attrs['comment'] = '= 0 for good soundings; = 1 for bad'

    # Assign averaging kernel and prior obs variables
    avgpro = dd['averaging_kernel_matrix'].values
    avgpro[avgpro == -999] = 0.
    avgker = np.sum(avgpro, axis=1)

    priorobs = np.sum(dd['priorpro'].values, axis=1)

    dd = dd.assign(avgker=(('nsound','navg'), avgker,
        {'units':'mol m-2 / mol m-2', 'long_name':'column averaging kernel'}))
    dd = dd.assign(priorobs=('nsound', priorobs, {'units':'mol m-2',
        'long_name':'carbon monoxide a priori total column in mole/m2',
        'standard_name':'atmosphere_mole_content_of_carbon_monoxide'}))

    # Assign edge dimension (nedge) and edge altitudes for avgker (zeavg)
    nedge = dd.sizes['navg'] + 1

    zsurf = dd.variables['surface_altitude'].values
    zgrid = np.arange(0,nedge*1000,1000, dtype=zsurf.dtype)
    zeavg = np.tile(zsurf, (nedge,1)).T + np.tile(zgrid, (nsound,1))

    dd = dd.assign(nedge=('nedge', np.arange(nedge, dtype='int32')))
    dd = dd.assign(zeavg=(('nsound','nedge'), zeavg, {'units':'m',
        'long_name':'altitude edges'}))

    dd = dd.drop_vars(('time_string', 'time_in_day', 'AERIStime',
        'hour', 'minute', 'day', 'solar_zenith_angle',
        'satellite_zenith_angle', 'orbit_number', 'scanline_number',
        'pixel_number', 'ifov_number', 'surface_altitude',
        'air_partial_column_profile', 'atmosphere_pressure_grid',
        'CO_partial_column_profile', 'CO_partial_column_error',
        'CO_degrees_of_freedom', 'averaging_kernel_matrix'), errors='ignore')

    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_ch4(fin, ftr):
    '''Translate IASI column CH4 retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = dd.rename({'sounding_dim':'nsound', 'layer_dim':'navg',
        'level_dim':'nedge', 'latitude':'lat', 'longitude':'lon',
        'pressure_levels':'peavg', 'ch4_quality_flag':'isbad', 'ch4':'obs',
        'ch4_uncertainty':'uncert', 'ch4_averaging_kernel':'avgker'})

#   # Replace averaging kernel with product of it and pwf
#   pwf = dd['pressure_weight']
#   avgker = dd['avgker']
#   avgker.values = avgker.values*pwf.values

    # Assign date and time vars
    ttin = dd['time'].values
    nsound = dd.sizes['nsound']

    date = np.zeros(nsound, dtype='int32')
    time = np.zeros(nsound, dtype='int32')

    for nn in range(nsound):
        tt = pd.Timestamp(ttin[nn])
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    dd = dd.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date'}))
    dd = dd.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding time'}))

    dd = dd.drop_vars(('solar_zenith_angle', 'sensor_zenith_angle',
        'pressure_weight'))

    dd.to_netcdf(ftr)
    dd.close()

    return None

# Will need to depend on version for co
translate = {
    'co':  translate_co,
    'ch4': translate_ch4}
