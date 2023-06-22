'''
Translate TROPESS retrievals to CoDAS format
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
import xarray as xr

PROUNIT = 'log10(mol/mol)'
OBSUNIT = 'mol/m^2'
OBSCONV = 1.0E5/(9.80665*28.965)

L10EXP = np.log10(np.exp(1.))

FILLSING = np.float32(-999.)
FILLINT  = np.int32(-999)

def translate(fin, ftr):
    '''Translate TROPESS retrievals to CoDAS format'''

    ds = xr.open_dataset(fin, mask_and_scale=False)
    dsobs = xr.open_dataset(fin, **{'group':'observation_ops'})
    ds = ds.assign(dsobs[['xa']])

    ds = ds.rename({'target':'nsound', 'level':'navg', 'time':'time_offset',
        'latitude':'lat', 'longitude':'lon', 'xa':'priorpro'})

    # Assign averaging kernel edge dimension (nedge) and pressures (peavg)
    pbotin = ds['pressure'].values
    NSOUND = ds.sizes['nsound']
    NAVG = ds.sizes['navg']

    ## Assume pressures are bottoms and top is 0.01 hPa
    ## *** SORT THIS OUT ***
    peavg = np.append(pbotin, 0.01*np.ones((NSOUND,1)), 1).astype(FILLSING.dtype)
    ## Fill
    for kk in reversed(range(NAVG)):
        inan = peavg[:,kk] == ds['pressure'].attrs['_FillValue']
        peavg[inan,kk] = peavg[inan,kk+1]

    ds = ds.assign(nedge=('nedge', np.arange(NAVG+1, dtype=FILLINT.dtype),
        {'units':'#', 'long_name':'vertical grid edge number'}))
    ds = ds.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'Edge pressures of averaging kernel',
        '_FillValue':FILLSING, 'missing_value':FILLSING}))

    # Compute pressure thickness (dpavg) and pressure weighting function (pwf)
    dpavg = peavg[:,:-1] - peavg[:,1:]
    pwf = OBSCONV * dpavg

    # Assign column obs (obs), a priori (priorpro), and uncertainty (uncert)
    obspro = ds['x'].values
    obs = np.sum(pwf*obspro, axis=1)

    priorpro = ds['priorpro'].values
    ## hack to deal with no missing/fill value
    priorpro[np.isnan(priorpro)] = np.finfo(priorpro.dtype).tiny
    priorobs = np.sum(pwf*priorpro, axis=1)

    ## Appears broken for CO: Should be -20s, but is O(1)
    uncpro = dsobs['observation_error'].values
    ## Correct overflow (why?!?)
    uncpro = np.minimum(uncpro, np.finfo(uncpro.dtype).max)
    uncert = np.zeros_like(obs)
    for kk in range(NAVG):
        uncert = uncert + np.sum(pwf*obspro*uncpro[:,:,kk], axis=1)

    ds = ds.assign(obs=('nsound', obs, {'units':OBSUNIT,
        'long_name':'Average column observation', '_FillValue':FILLSING,
        'missing_value':FILLSING}))
    ds = ds.assign(priorobs=('nsound', priorobs, {'units':OBSUNIT,
        'long_name':'Average column a priori', '_FillValue':FILLSING,
        'missing_value':FILLSING}))
    ds = ds.assign(uncert=('nsound', uncert, {'units':OBSUNIT,
        'long_name':'Average column uncertainty', '_FillValue':FILLSING,
        'missing_value':FILLSING}))

    # Assign column averaging kernel (avgker)
    avgkin = dsobs['averaging_kernel'].values
    avgker = np.zeros_like(pwf)

    ## Check averaging kernel transpose & correct log transform
    ## Should be both multiplying by obspro and dividing by ...?
    for ii in range(NAVG):
        avgadd = pwf*avgkin[:,:,ii]*obspro/L10EXP
#       for jj in range(NAVG):
#           avgadd[:,jj] = avgadd[:,jj]/priorpro[:,jj]*L10EXP
        avgker = avgker + avgadd

    ds = ds.assign(avgker=(('nsound','navg'), avgker,
        {'units':OBSUNIT+' / '+PROUNIT, 'long_name':'Averaging kernel',
        '_FillValue':FILLSING, 'missing_value':FILLSING}))

    # Convert prior profile from mol/mol to log10(mol/mol)
    ds['priorpro'].values = np.log10(priorpro)
    ds['priorpro'].attrs['units'] = PROUNIT
    ds['priorpro'].attrs['comment'] = 'A priori profile'

    # Assign date and time
    dvecs = ds['datetime_utc'].values.astype(FILLINT.dtype)

    date = dvecs[:,0]*10000 + dvecs[:,1]*100 + dvecs[:,2]
    time = dvecs[:,3]*10000 + dvecs[:,4]*100 + dvecs[:,5]

    ## Is this even needed?
    inan = np.logical_or.reduce(
        dvecs == ds['datetime_utc'].attrs['_FillValue'], 1)
    date[inan] = FILLINT
    time[inan] = FILLINT

    ds = ds.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', '_FillValue':FILLINT}))
    ds = ds.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding date', '_FillValue':FILLINT}))

    # Sort (why?!?)
    ds = ds.sortby('time')

    # Finish up
    ds = ds.drop(('datetime_utc', 'time_offset', 'year_fraction', 'pressure',
        'altitude', 'x'))

    ds.to_netcdf(ftr)
    ## Safer this way, crashes other ways on some machines
    ds.close()
    dsobs.close()

    return None
