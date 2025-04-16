'''
Translate MOPITT retrievals to CoDAS format
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

from datetime import datetime, timedelta

import numpy as np
import netCDF4
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

NEDGE = 11

PROUNIT = 'ppb'
OBSUNIT = 'ppb'

DFSMIN = 0.25			# Minimum degrees-of-freedom (#)
TSMAX  =  46.00	+ 273.15	# Maximum TIR surface temperature (K)
TSMIN  = -15.00 + 273.15	# Maximum TIR surface temperature (K)
NIRSZA = 60			# Maximum NIR solar zenith angle (deg)

FILLINT = np.int32(-9999)

def translate(fin, ftr, radtype):
    '''Translate MOPITT retrievals to CoDAS format'''

    ncf = netCDF4.Dataset(fin, diskless=True, persist=False)
    ncdata = ncf['HDFEOS/SWATHS/MOP02/Data Fields']
    ncloc  = ncf['HDFEOS/SWATHS/MOP02/Geolocation Fields']
    ncattr = ncf['HDFEOS/ADDITIONAL/FILE_ATTRIBUTES']

    dsdata = xr.open_dataset(xr.backends.NetCDF4DataStore(ncdata))
    dsloc  = xr.open_dataset(xr.backends.NetCDF4DataStore(ncloc))
    dsattr = xr.open_dataset(xr.backends.NetCDF4DataStore(ncattr))

    # Copy and rename variables w/ appropriate dimensions
    ds = dsdata[['APrioriCOTotalColumn', 'TotalColumnAveragingKernel']]
    ds = ds.assign(dsloc[['Latitude', 'Longitude']])
    ds = ds.rename({'nTime':'nsound', 'nPrs2':'navg', 'Latitude':'lat',
        'Longitude':'lon', 'APrioriCOTotalColumn':'priorobs',
        'TotalColumnAveragingKernel':'avgker'})

    inan = np.isnan(ds['avgker'].values)
    ds['avgker'].values[inan] = 0.

    ds.attrs['conversion'] = '6.02214076E19 molec cm-2 = 1 mol m-2'

    # Dimension sizes needed below
    nsound = ds.sizes['nsound']
    navg   = ds.sizes['navg']

    # Assign date and time
    year  = dsattr.attrs['Year']
    month = dsattr.attrs['Month']
    day   = dsattr.attrs['Day']
    secs  = dsloc['SecondsinDay'].values

    date = np.zeros(nsound, dtype=FILLINT.dtype)
    time = np.zeros(nsound, dtype=FILLINT.dtype)

    for nn in range(nsound):
        tt = datetime(year,month,day) + timedelta(seconds=int(secs[nn]))
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    inan = np.isnan(secs)
    date[inan] = FILLINT
    time[inan] = FILLINT

    ds = ds.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', '_FillValue':FILLINT}))
    ds = ds.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding date', '_FillValue':FILLINT}))

    # Assign pressure edges
    psurf = dsdata['SurfacePressure'].values
    peavg = np.zeros((nsound,NEDGE), dtype=psurf.dtype)
    peavg[:,0] = psurf
    for kk in range(1,NEDGE-1):
        peavg[:,kk] = 1000. - kk*100.
        peavg[:,kk] = np.minimum(peavg[:,kk], psurf)
    peavg[:,NEDGE-1] = 26.

    ds = ds.assign(nedge=('nedge', np.arange(NEDGE, dtype=FILLINT.dtype),
        {'units':'#', 'long_name':'vertical grid edge number'}))
    ds = ds.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    # Assign prior obs, obs, and uncert
    tcoapr = dsdata['APrioriCOTotalColumn'].values
    tcoret = dsdata['RetrievedCOTotalColumn'].values
    drycol = dsdata['DryAirColumn'].values

    ## Transform totals to ppb
    priorobs = tcoapr / drycol * 1.e9
    obs = tcoret[:,0] / drycol * 1.e9
    uncert = tcoret[:,1] / drycol * 1.e9
    for kk in range(navg):
        ds['avgker'].values[:,kk] = ds['avgker'].values[:,kk] / drycol * 1.e9

    ds = ds.assign(priorobs=('nsound', priorobs, {'units':OBSUNIT,
        'long_name':'prior obs'}))
    ds = ds.assign(obs=('nsound', obs, {'units':OBSUNIT,
        'long_name':'obs value'}))
    ds = ds.assign(uncert=('nsound', uncert, {'units':OBSUNIT,
        'long_name':'obs uncertainty'}))
    ds = ds.assign(drycol=('nsound', drycol, {'units':'# cm-2',
        'long_name':'dry air column'}))

    # Assign quality flags
    qc5 = dsdata['RetrievalAnomalyDiagnostic'].values
    tsurf = dsdata['RetrievedSurfaceTemperature'].values
    dfs = dsdata['DegreesofFreedomforSignal'].values
    sza = dsdata['SolarZenithAngle'].values
    isbad = np.sum(qc5, axis=1) + (tcoret[:,0] <= 0) + (dfs < DFSMIN)
    if (radtype[0].upper() == 'N'):
        isbad = isbad + (tsurf[:,0] < TSMIN) + (NIRSZA < sza)
    else:
        isbad = isbad + (TSMAX < tsurf[:,0])

    ds = ds.assign(isbad=('nsound', isbad, {'units':'none',
        'long_name':'obs flagged as bad?'}))

    # Assign prior profile
    scoapr = dsdata['APrioriCOSurfaceMixingRatio'].values
    pcoapr = dsdata['APrioriCOMixingRatioProfile'].values
    priorpro = np.zeros((nsound,navg), dtype=scoapr.dtype)

    for nn in range(nsound):
        ksurf = np.argmax(peavg[nn,:] < psurf[nn])
        ## Fill layers up to surface w/ surface value
        for kk in range(ksurf):
            priorpro[nn,kk] = scoapr[nn,0]
        ## Fill layers above surface w/ profile values
        for kk in range(ksurf,navg):
            priorpro[nn,kk] = pcoapr[nn,kk-1,0]

    ds = ds.assign(priorpro=(('nsound','navg'), priorpro, {'units':PROUNIT,
        'long_name':'prior profile'}))

    ## Convert averaging kernel from taking log10(mol/mol) to ppb
    ds['avgker'].values = ds['avgker'].values / (priorpro * np.log(10.))
    ds['avgker'].attrs['units'] = OBSUNIT + ' / ' + PROUNIT

    # Finish up
    ds.to_netcdf(ftr)
    ds.close()
    # Safer this way, crashes other ways on some machines
    dsdata.close()

    return None
