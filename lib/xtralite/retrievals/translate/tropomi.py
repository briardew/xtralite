'''
Translate TROPOMI retrievals to xtralite
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

def _generic(ftr):
    '''Does the generic stuff'''

#   Create sounding number (nsound), date and time variables
    ncf = netCDF4.Dataset(ftr, 'a')

    dvecs = ncf.variables['date_components'][:].astype(int)
    dates = ncf.createVariable('date', 'i4', (RECDIM,))
    times = ncf.createVariable('time', 'i4', (RECDIM,))

    dates[:] = dvecs[:,0]*10000 + dvecs[:,1]*100 + dvecs[:,2]
    times[:] = dvecs[:,3]*10000 + dvecs[:,4]*100 + dvecs[:,5]

    dates.units = 'YYYYMMDD'
    times.units = 'hhmmss'
    dates.long_name = 'Sounding date'
    times.long_name = 'Sounding time'
    dates.missing_value = np.int32(-9999)
    times.missing_value = np.int32(-9999)

#   Create prior column variable (priorobs)
    apro = ncf.variables['priorpro']
    acol = ncf.createVariable('priorobs', 'f4', (RECDIM,))
    acol.units = 'mol m-2'
    acol.long_name = 'Total column a priori'
    acol.missing_value = np.float32(-999999.)
    acol[:] = np.sum(apro[:], axis=1)

    ncf.close()

#   Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v', 'sounding,sounding_id,' +
        'date_components,time_offset,layer,qa_value,footprint,' +
        'surface_classification,surface_pressure,solar_zenith_angle',
        ftr, ftr])

    return None

def translate_ch4(fin, ftr):
    '''Translate TROPOMI column CH4 retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-d', 'level,nedge',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'altitude_levels,zeavg',
        '-v', 'methane_mixing_ratio_bias_corrected,obs',
        '-v', 'methane_mixing_ratio_precision,uncert',
        '-v', 'column_averaging_kernel,avgker',
        '-v', 'methane_profile_apriori,priorpro', ftr, ftr])

#   3. Convert obs and uncert to mol m-2
#   (averaging kernel has units of "1", so seems legit?)
    ncf = netCDF4.Dataset(ftr, 'a') 

    dry  = ncf.variables['dry_air_subcolumns']
    xcol = ncf.variables['obs']
    ucol = ncf.variables['uncert']
    xcol.units = 'mol m-2'
    ucol.units = 'mol m-2'
    xcol[:] = 1.e-9 * xcol[:] * np.sum(dry[:], axis=1)
    ucol[:] = 1.e-9 * ucol[:] * np.sum(dry[:], axis=1)

    ncf.close()

#   4. Do generic stuff
    _generic(ftr)

#   5. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'level,dry_air_subcolumns,methane_mixing_ratio', ftr, ftr])

    return None

def translate_co(fin, ftr):
    '''Translate TROPOMI column CO retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'carbonmonoxide_total_column,obs',
        '-v', 'carbonmonoxide_total_column_precision,uncert',
        '-v', 'column_averaging_kernel,avgker', ftr, ftr])

#   3. Create edge dim (nedge) and pressure edges of avgker var (peavg)
    ncf = netCDF4.Dataset(ftr, 'a') 

    avgker = ncf.variables['avgker']
    nedge  = ncf.createDimension('nedge', size=avgker[:].shape[1] + 1)
    zeavg  = ncf.createVariable('zeavg', 'f4', (RECDIM,'nedge'))
#   vectorize this
    for nn in range(avgker[:].shape[0]):
        zeavg[nn,:] = range(0,nedge.size*1000,1000)

    ncf.close()

#   4. Do generic stuff
    _generic(ftr)

#   5. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'height_scattering_layer', ftr, ftr])

    return None

def translate_hcho(fin, ftr):
    '''Translate TROPOMI column HCHO retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'formaldehyde_tropospheric_vertical_column,obs',
        '-v', 'formaldehyde_tropospheric_vertical_column_precision,uncert',
        '-v', 'averaging_kernel,avgker',
        '-v', 'formaldehyde_profile_apriori,priorpro', ftr, ftr])

#   3. Create edge dim (nedge) and pressure edges of avgker var (peavg)
    ncf = netCDF4.Dataset(ftr, 'a')

    ak = ncf.variables['tm5_constant_a']
    bk = ncf.variables['tm5_constant_b']
    psurf = ncf.variables['surface_pressure']
    nedge = ncf.createDimension('nedge', size=ak[:].shape[1]+1)
    peavg = ncf.createVariable('peavg', 'f4', (RECDIM,'nedge'))
    peavg.units     = 'hPa'
    peavg.long_name = 'Pressure edges for averaging kernel'
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge.size-1):
        peavg[:,kk+1] = 1.e-2 * (ak[:,kk] + bk[:,kk]*psurf[:])

    ncf.close()

#   4. Do generic stuff
    _generic(ftr)

#   5. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'cloud_fraction_crb,tm5_constant_a,tm5_constant_b,' +
        'formaldehyde_tropospheric_vertical_column_trueness', ftr, ftr])

    return None

def translate_so2(fin, ftr):
    '''Translate TROPOMI column SO2 retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'sulfurdioxide_total_vertical_column,obs',
        '-v', 'sulfurdioxide_total_vertical_column_precision,uncert',
        '-v', 'averaging_kernel,avgker',
        '-v', 'sulfurdioxide_profile_apriori,priorpro', ftr, ftr])

#   3. Create edge dim (nedge) and pressure edges of avgker var (peavg)
    ncf = netCDF4.Dataset(ftr, 'a')

    ak = ncf.variables['tm5_constant_a']
    bk = ncf.variables['tm5_constant_b']
    psurf = ncf.variables['surface_pressure']
    nedge = ncf.createDimension('nedge', size=ak[:].shape[1]+1)
    peavg = ncf.createVariable('peavg', 'f4', (RECDIM,'nedge'))
    peavg.units     = 'hPa'
    peavg.long_name = 'Pressure edges for averaging kernel'
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge.size-1):
        peavg[:,kk+1] = 1.e-2 * (ak[:,kk] + bk[:,kk]*psurf[:])

    ncf.close()

#   4. Do generic stuff
    _generic(ftr)

#   5. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'cloud_fraction_crb,tm5_constant_a,tm5_constant_b,' +
        'sulfurdioxide_total_vertical_column_trueness', ftr, ftr])

    return None

def translate_no2(fin, ftr):
    '''Translate TROPOMI column NO2 retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'nitrogendioxide_summed_total_column,obs',
        '-v', 'nitrogendioxide_summed_total_column_precision,uncert',
        '-v', 'averaging_kernel,avgker', ftr, ftr])

#   3. Create edge dim (nedge) and pressure edges of avgker var (peavg)
    ncf = netCDF4.Dataset(ftr, 'a')

    ak = ncf.variables['tm5_constant_a']
    bk = ncf.variables['tm5_constant_b']
    psurf = ncf.variables['surface_pressure']
    nedge = ncf.createDimension('nedge', size=ak[:].shape[1]+1)
    peavg = ncf.createVariable('peavg', 'f4', (RECDIM,'nedge'))
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge.size-1):
        peavg[:,kk+1] = 1.e-2 * (ak[kk] + bk[kk]*psurf[:])

    ncf.close()

#   4. Do generic stuff
    _generic(ftr)

#   5. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'cloud_fraction_crb,tm5_constant_a,tm5_constant_b', ftr, ftr])

    return None

def translate_o3(fin, ftr):
    '''Translate TROPOMI column O3 retrievals to xtralite'''
#   1. Flatten groups
    pout = check_call(['ncks', '-O', '-G', ':', fin, ftr])

#   2. Rename dimensions and variables
    pout = check_call(['ncrename', '-O',
        '-d', 'sounding,'+RECDIM,
        '-d', 'layer,navg',
        '-d', 'level,nedge',
        '-v', 'date,date_components',
        '-v', 'time,time_offset',
        '-v', 'latitude,lat',
        '-v', 'longitude,lon',
        '-v', 'pressure_grid,peavg',
        '-v', 'ozone_total_vertical_column,obs',
        '-v', 'ozone_total_vertical_column_precision,uncert',
        '-v', 'averaging_kernel,avgker',
        '-v', 'ozone_profile_apriori,priorpro', ftr, ftr])

#   3. Do generic stuff
    _generic(ftr)

#   4. Delete extra variables
    pout = check_call(['ncks', '-O', '-x', '-v',
        'cloud_fraction_crb,level', ftr, ftr])

    return None

translate = {
    'ch4':  translate_ch4,
    'co':   translate_co,
    'hcho': translate_hcho,
    'so2':  translate_so2,
    'no2':  translate_no2,
    'o3':   translate_o3}
