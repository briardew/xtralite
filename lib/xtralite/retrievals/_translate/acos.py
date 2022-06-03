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

import datetime as dtm
import numpy as np
import netCDF4
from subprocess import call

RECDIM = 'sounding_id'

def oco(fin, ftr):
    '''Translate ACOS XCO2 OCO retrievals to xtralite'''
#   1. Make some adjustments so chunking runs quicker
    pout = call(['cp', '-f', fin, ftr])
    pout = call(['ncks', '-h', '-A', '-G', ':1', '-g', 'Retrieval',
        '-v', 'psurf,surface_type', ftr, ftr])
    pout = call(['ncks', '-h', '-A', '-G', ':1', '-g', 'Retrieval',
        '-v', 'aod_dust,aod_bc,aod_oc,aod_seasalt,aod_sulfate,' +
        'aod_strataer,aod_water,aod_ice,aod_total,tcwv,xco2_raw', ftr, ftr])
    pout = call(['ncks', '-h', '-A', '-G', ':1', '-g', 'Sounding',
        '-v', 'operation_mode,footprint,glint_angle', ftr, ftr])
    pout = call(['ncks', '-h', '-A', '-G', ':1', '-g', 'Meteorology',
        '-v', 'psurf_apriori', ftr, ftr])

#   2. Recast sounding_id, otherwise this is very slow
    pout = call(['ncap2', '-O', '-s', 'sounding_id=int(sounding_id)', ftr, ftr])
    pout = call(['ncks', '-O', '-3', '-C', '-x', '-v', 'source_files,' +
        'file_index,vertex_latitude,vertex_longitude', ftr, ftr])
    pout = call(['ncks', '-O', '--mk_rec_dmn', 'sounding_id', ftr, ftr])

#   3. Rename dimensions and variables
    pout = call(['ncrename', '-v', 'xco2,xco2_final', ftr])
    pout = call(['ncrename', '-v', 'xco2_uncertainty,xco2_uncert', ftr])
    pout = call(['ncrename', '-v', 'xco2_averaging_kernel,xco2_avgker', ftr])
    pout = call(['ncrename', '-v', 'xco2_quality_flag,qcflag', ftr])

    pout = call(['ncrename', '-v', 'pressure_weight,pwf', ftr])

#   4. Replace averaging kernel with product of it and pwf
    ncf = netCDF4.Dataset(ftr, 'a') 

    pwf    = ncf.variables['pwf']
    avgker = ncf.variables['xco2_avgker']
    avgker[:] = avgker[:]*pwf[:]

#   5. Create sounding_date and sounding_time variables
    dvecs = ncf.variables['date'][:].astype(int)

    dates = ncf.createVariable('sounding_date', 'i4', (RECDIM,))
    times = ncf.createVariable('sounding_time', 'i4', (RECDIM,))

    dates[:] = dvecs[:,0]*10000 + dvecs[:,1]*100 + dvecs[:,2]
    times[:] = dvecs[:,3]*10000 + dvecs[:,4]*100 + dvecs[:,5]

    dates.units         = 'YYYYMMDD'
    dates.long_name     = 'Sounding Date'
    dates.missing_value = np.int32(-9999)
    times.units         = 'hhmmss'
    times.long_name     = 'Sounding Time'
    times.missing_value = np.int32(-9999)
    times.comment       = 'from scan start time in UTC'

    ncf.close()

    return None

def gosat(fin, ftr):
    '''Translate ACOS XCO2 GOSAT retrievals to xtralite'''
#   1. Flatten groups and rename dimensions and variables
    pout = call(['ncks', '-O', '-G', ':', fin, ftr])
    pout = call(['ncrename', '-v', 'xco2,xco2_final', ftr])
    pout = call(['ncrename', '-v', 'xco2_uncertainty,xco2_uncert', ftr])
    pout = call(['ncrename', '-v', 'xco2_averaging_kernel,xco2_avgker', ftr])
    pout = call(['ncrename', '-v', 'xco2_quality_flag,qcflag', ftr])

    pout = call(['ncrename', '-v', 'pressure_weight,pwf', ftr])

#   2. Replace averaging kernel with product of it and pwf
    ncf = netCDF4.Dataset(ftr, 'a') 

    pwf    = ncf.variables['pwf']
    avgker = ncf.variables['xco2_avgker']
    avgker[:] = avgker[:]*pwf[:]

#   4. Create sounding_date and sounding_time variables
    dvecs = ncf.variables['date'][:].astype(int)

    dates = ncf.createVariable('sounding_date', 'i4', (RECDIM,))
    times = ncf.createVariable('sounding_time', 'i4', (RECDIM,))

    dates[:] = dvecs[:,0]*10000 + dvecs[:,1]*100 + dvecs[:,2]
    times[:] = dvecs[:,3]*10000 + dvecs[:,4]*100 + dvecs[:,5]

    dates.units         = 'YYYYMMDD'
    dates.long_name     = 'Sounding Date'
    dates.missing_value = np.int32(-9999)
    times.units         = 'hhmmss'
    times.long_name     = 'Sounding Time'
    times.missing_value = np.int32(-9999)
    times.comment       = 'from scan start time in UTC'

#   5. Translate gain to operation mode
    gain = ncf.variables['gain'][:]
    mode = ncf.createVariable('operation_mode', 'i1', (RECDIM,))

    mode[:] = 127
    for ir in range(len(gain)):
        if gain[ir] == b'M': mode[ir] = 0
        if gain[ir] == b'H': mode[ir] = 1

    mode.units         = 'none'
    mode.long_name     = 'GOSAT Operation Mode: 0=M-gain, 1=H-gain'
    mode.missing_value = 127
    mode.comment       = ''

    ncf.close()

    return None
