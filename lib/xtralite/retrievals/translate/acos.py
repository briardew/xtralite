'''
Translate ACOS retrievals to xtralite
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

import numpy as np
#import xarray as xr
from xtralite.patches import xarray as xr

def _generic(dd):
#   Rename dims and vars
    dd = dd.rename({'xco2':'xco2_final', 'xco2_uncertainty':'xco2_uncert',
        'xco2_averaging_kernel':'xco2_avgker', 'xco2_quality_flag':'qcflag',
        'pressure_weight':'pwf'})

#   Do anything to sounding_id and levels dims?
    dd['sounding_id'] = dd['sounding_id'].astype('int32')

#   Create date and time vars
    dvec = dd['date'].values.astype('int32')
    nsound = dd.sizes['sounding_id']

    date = np.zeros(nsound, dtype='int32')
    time = np.zeros(nsound, dtype='int32')

    date = dvec[:,0]*10000 + dvec[:,1]*100 + dvec[:,2]
    time = dvec[:,3]*10000 + dvec[:,4]*100 + dvec[:,5]

    dd = dd.assign(sounding_date=('sounding_id', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', 'missing_value':np.int32(-9999)}))
    dd = dd.assign(sounding_time=('sounding_id', time, {'units':'hhmmss',
        'long_name':'sounding time', 'missing_value':np.int32(-9999)}))

#   Replace averaging kernel with product of it and pwf
    pwf    = dd['pwf']
    avgker = dd['xco2_avgker']
    avgker.values = avgker.values*pwf.values

#   Drop common vars
    dd = dd.drop_vars(('bands', 'date', 'time', 'solar_zenith_angle',
        'sensor_zenith_angle', 'xco2_qf_bitflag', 'source_files',
        'file_index'))

    return dd

def gosat(fin, ftr):
    '''Translate ACOS XCO2 GOSAT retrievals to xtralite'''

#   Open and add needed group vars
    dd = xr.open_dataset(fin)
    ddret = xr.open_dataset(fin, **{'group':'Retrieval'})
    ddsnd = xr.open_dataset(fin, **{'group':'Sounding'})
    dd = dd.assign(ddret[['psurf', 'surface_type']])
    dd = dd.assign(ddsnd[['gain']])
    ddret.close()
    ddsnd.close()

#   Do generic stuff
    dd = _generic(dd)

#   Translate gain to operation mode
    gain = dd['gain'].values
    nsound = dd.sizes['sounding_id']
    mode = 127*np.ones(nsound, dtype='int8')

    for ii in range(nsound):
        if gain[ii] == b'M': mode[ii] = 0
        if gain[ii] == b'H': mode[ii] = 1

    dd = dd.assign(mode=('sounding_id', mode, {'units':'none',
        'long_name':'GOSAT Operation Mode: 0=M-gain, 1=H-gain',
        'missing_value':np.int8(127), 'comment':''}))

#   Drop vars, write, and close
    dd = dd.drop_vars(('gain'))
    dd.to_netcdf(ftr)
    dd.close()

    return None

def oco(fin, ftr):
    '''Translate ACOS XCO2 OCO retrievals to xtralite'''

#   Open and add needed group vars
    dd = xr.open_dataset(fin)
    ddret = xr.open_dataset(fin, **{'group':'Retrieval'})
    ddsnd = xr.open_dataset(fin, **{'group':'Sounding'})
    dd = dd.assign(ddret[['psurf', 'surface_type']])
    dd = dd.assign(ddsnd[['operation_mode']])
    ddret.close()
    ddsnd.close()

#   Do generic stuff
    dd = _generic(dd)

#   Drop vars, write, and close
    dd = dd.drop_vars(('vertex_latitude', 'vertex_longitude', 'vertices',
        'footprints', 'xco2_qf_simple_bitflag'), errors='ignore')
    dd.to_netcdf(ftr)
    dd.close()

    return None
