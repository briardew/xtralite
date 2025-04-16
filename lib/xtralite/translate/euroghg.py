'''
Translate European GHG retrievals to CoDAS format
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
#===============================================================================

import numpy as np
import pandas as pd
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

RECDIM = 'nsound'

def translate(fin, ftr, var):
    '''Translate European GHG retrievals to CoDAS format'''

    varlo = var.lower()

    dd = xr.open_dataset(fin)
    if 'sounding_dim' in dd.dims:
        dd = dd.rename({'sounding_dim':RECDIM, 'layer_dim':'navg',
            'level_dim':'nedge'})
    else:
        dd = dd.rename({'n':RECDIM, 'm':'navg'})
        dd = dd.assign_coords(nedge=np.arange(10).astype('int32'))

    # Clobber and recast sounding number
    nsound = dd.sizes[RECDIM]
    dd = dd.assign_coords({RECDIM:np.arange(nsound).astype('int32')})

    dd = dd.rename({'time':'time_offset',
        'latitude':'lat', 'longitude':'lon',
        'pressure_levels':'peavg', 'x'+varlo:'obs',
        'x'+varlo+'_uncertainty':'uncert',
        'x'+varlo+'_quality_flag':'isbad',
        'x'+varlo+'_averaging_kernel':'avgker',
        varlo+'_profile_apriori':'priorpro'})

    # Assign date and time variables
    dt64 = dd['time_offset'].values

    date = np.zeros(nsound, dtype=np.int32)
    time = np.zeros(nsound, dtype=np.int32)

    for nn in range(nsound):
        tt = pd.Timestamp(dt64[nn])
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    dd = dd.assign(date=(RECDIM, date, {'units':'YYYYMMDD',
        'long_name':'sounding date'}))
    dd = dd.assign(time=(RECDIM, time, {'units':'hhmmss',
        'long_name':'sounding time'}))

    # Sort -- Chunker will die if time is non-increasing
    dd = dd.sortby('time')

    # Replace averaging kernel with product of it and pwf
    pwf = dd['pressure_weight'].values
    avgker = dd['avgker']
    avgker.values = avgker.values*pwf

    # Assign prior column variable (priorobs)
    apro = dd['priorpro']
    acol = np.sum(pwf*apro.values, axis=1)
    dd = dd.assign(priorobs=(RECDIM, acol, {'units':apro.units,
        'long_name':'A priori X' + var.upper() + ' Value'}))

    dd = dd[['date', 'time', 'lat', 'lon', 'peavg', 'obs', 'uncert', 'isbad',
        'avgker', 'priorpro', 'priorobs']]
    dd.to_netcdf(ftr)
    dd.close()

    return None
