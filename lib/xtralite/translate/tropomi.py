'''
Translate TROPOMI retrievals to CoDAS format
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
# * Why is navg coordinate a float?
# * Fix/delete? coordinates and bounds variable attributes
#===============================================================================

import numpy as np
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

FILLINT = -9999

def _generic_beg(dd):
    dd = dd.rename({'sounding':'nsound', 'layer':'navg',
        'date':'date_components', 'time':'time_offset', 'latitude':'lat',
        'longitude':'lon'})

    # Redefine navg to index
    navg = dd.sizes['navg']
    dd = dd.assign_coords(navg=np.arange(navg, dtype='int32'))

    # Assign date and time variables
    dvec = dd.variables['date_components'].values.astype('int32')
    nsound = dd.sizes['nsound']

    date = np.zeros(nsound, dtype='int32')
    time = np.zeros(nsound, dtype='int32')

    date = dvec[:,0]*10000 + dvec[:,1]*100 + dvec[:,2]
    time = dvec[:,3]*10000 + dvec[:,4]*100 + dvec[:,5]

    dd = dd.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', '_FillValue':np.int32(FILLINT)}))
    dd = dd.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding time', '_FillValue':np.int32(FILLINT)}))

    return dd

def _generic_end(dd):
    # Create prior column if prior profile exists
    if 'priorpro' in dd.variables:
        apro = dd.variables['priorpro']
        acol = np.sum(apro.values, axis=1)
        attrs = {'units':'mol m-2', 'long_name':'total column a priori'}
        dd = dd.assign(priorobs=('nsound', acol, attrs))

    dd = dd.drop_vars(('sounding_id', 'date_components', 'time_offset',
        'qa_value', 'footprint', 'surface_classification',
        'surface_pressure', 'solar_zenith_angle', 'processing_quality_flags'))

    # Delete global attributes too?
    # Delete variable attributes that are no longer valid

    return dd

def translate_co(fin, ftr):
    '''Translate TROPOMI column CO retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'carbonmonoxide_total_column':'obs',
        'carbonmonoxide_total_column_precision':'uncert',
        'column_averaging_kernel':'avgker'})

    # Assign edge dimension (nedge) and edge altitudes for avgker (zeavg)
    nsound = dd.sizes['nsound']
    nedge  = dd.sizes['navg'] + 1

    zsurf = dd.variables['surface_altitude'].values
    zgrid = np.flip(np.arange(0,nedge*1000,1000, dtype='float32'))
    zeavg = np.tile(zsurf, (nedge,1)).T + np.tile(zgrid, (nsound,1))

    dd = dd.assign(nedge=('nedge', np.arange(nedge, dtype='int32')))
    dd = dd.assign(zeavg=(('nsound','nedge'), zeavg, {'units':'m',
        'long_name':'altitude edges'}))

    dd = dd.drop_vars('surface_altitude')

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_ch4(fin, ftr):
    '''Translate TROPOMI column CH4 retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'level':'nedge', 'altitude_levels':'zeavg',
        'methane_mixing_ratio_bias_corrected':'obs',
        'methane_mixing_ratio_precision':'uncert',
        'column_averaging_kernel':'avgker',
        'methane_profile_apriori':'priorpro'})

    # Convert obs and uncert to mol m-2
    # (avgker has units of "1", so seems legit?)
    dry = dd.variables['dry_air_subcolumns']

    xcol = dd.variables['obs']
    xcol.values = 1.e-9 * xcol.values * np.sum(dry.values, axis=1)
    xcol.attrs['units'] = 'mol m-2'
    xcol.attrs['standard_name'] = 'atmosphere_mole_content_of_methane'
    xcol.attrs['long_name'] = 'Vertically integrated CH4 column'

    ucol = dd.variables['uncert']
    ucol.values = 1.e-9 * ucol.values * np.sum(dry.values, axis=1)
    ucol.attrs['units'] = 'mol m-2'
    ucol.attrs['standard_name'] = ('atmosphere_mole_content_of_methane ' +
        'standard_error')
    ucol.attrs['long_name'] = ('Standard error of the vertically ' +
        'integrated CH4 column')

    dd = dd.drop_vars(('dry_air_subcolumns', 'methane_mixing_ratio'))

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_hcho(fin, ftr):
    '''Translate TROPOMI column HCHO retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'formaldehyde_tropospheric_vertical_column':'obs',
        'formaldehyde_tropospheric_vertical_column_precision':'uncert',
        'averaging_kernel':'avgker',
        'formaldehyde_profile_apriori':'priorpro'})

    # Assign edge dimension (nedge) and edge pressures for avgker (peavg)
    ak = dd.variables['tm5_constant_a'].values
    bk = dd.variables['tm5_constant_b'].values
    psurf = dd.variables['surface_pressure'].values

    nsound = dd.sizes['nsound']
    nedge  = dd.sizes['navg'] + 1

    peavg = np.zeros((nsound,nedge), dtype='float32')
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge-1):
        peavg[:,kk+1] = 1.e-2 * (ak[:,kk] + bk[:,kk]*psurf)

    dd = dd.assign(nedge=('nedge', np.arange(nedge, dtype='int32')))
    dd = dd.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    dd = dd.drop_vars(('cloud_fraction_crb', 'tm5_constant_a',
        'tm5_constant_b',
        'formaldehyde_tropospheric_vertical_column_trueness'))

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_so2(fin, ftr):
    '''Translate TROPOMI column SO2 retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'sulfurdioxide_total_vertical_column':'obs',
        'sulfurdioxide_total_vertical_column_precision':'uncert',
        'averaging_kernel':'avgker',
        'sulfurdioxide_profile_apriori':'priorpro'})

    # Assign edge dimension (nedge) and edge pressures for avgker (peavg)
    ak = dd.variables['tm5_constant_a'].values
    bk = dd.variables['tm5_constant_b'].values
    psurf = dd.variables['surface_pressure'].values

    nsound = dd.sizes['nsound']
    nedge  = dd.sizes['navg'] + 1

    peavg = np.zeros((nsound,nedge), dtype='float32')
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge-1):
        peavg[:,kk+1] = 1.e-2 * (ak[:,kk] + bk[:,kk]*psurf)

    dd = dd.assign(nedge=('nedge', np.arange(nedge, dtype='int32')))
    dd = dd.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    dd = dd.drop_vars(('cloud_fraction_crb', 'tm5_constant_a',
        'tm5_constant_b', 'sulfurdioxide_total_vertical_column_trueness'))

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_no2(fin, ftr):
    '''Translate TROPOMI column NO2 retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'nitrogendioxide_summed_total_column':'obs',
        'nitrogendioxide_slant_column_density':'slant',
        'nitrogendioxide_summed_total_column_precision':'uncert',
        'averaging_kernel':'avgker'})

    # Assign edge dimension (nedge) and edge pressures for avgker (peavg)
    ak = dd.variables['tm5_constant_a'].values
    bk = dd.variables['tm5_constant_b'].values
    psurf = dd.variables['surface_pressure'].values

    nsound = dd.sizes['nsound']
    nedge  = dd.sizes['navg'] + 1

    peavg = np.zeros((nsound,nedge), dtype='float32')
    peavg[:,0] = 1.e-2 * psurf[:]
    for kk in range(nedge-1):
#       Note extra dimension for NO2 and not SO2 and HCHO
        peavg[:,kk+1] = 1.e-2 * (ak[:,kk,1] + bk[:,kk,1]*psurf)

    dd = dd.assign(nedge=('nedge', np.arange(nedge, dtype='int32')))
    dd = dd.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    dd = dd.drop_vars(('cloud_fraction_crb', 'tm5_constant_a',
        'tm5_constant_b', 'vertices'))

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

def translate_o3(fin, ftr):
    '''Translate TROPOMI column O3 retrievals to CoDAS format'''

    dd = xr.open_dataset(fin)
    dd = _generic_beg(dd)

    dd = dd.rename({'level':'nedge', 'pressure_grid':'peavg',
        'ozone_total_vertical_column':'obs',
        'ozone_total_vertical_column_precision':'uncert',
        'averaging_kernel':'avgker',
        'ozone_profile_apriori':'priorpro'})

    dd = dd.drop_vars('cloud_fraction_crb')

    dd = _generic_end(dd)
    dd.to_netcdf(ftr)
    dd.close()

    return None

translate = {
    'ch4':  translate_ch4,
    'co':   translate_co,
    'hcho': translate_hcho,
    'so2':  translate_so2,
    'no2':  translate_no2,
    'o3':   translate_o3
}
