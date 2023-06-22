'''
Translate MOPITT retrievals to CoDAS format
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
import netCDF4
from datetime import datetime, timedelta

NEDGE = 11

PROUNIT = 'log10(mol/mol)'
OBSUNIT = 'mol/m^2'
OBSCONV = 6.02214076E19

DFSMIN = 0.25			# Minimum degrees-of-freedom (#)
TSMAX  = 320			# Maximum surface temperature (K)
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

    # Assign prior obs, obs, and uncert
    tcoapr = dsdata['APrioriCOTotalColumn'].values
    tcoret = dsdata['RetrievedCOTotalColumn'].values
    drycol = dsdata['DryAirColumn'].values

    ## Convert from #/cm^2 to mol/m^2
    priorobs = tcoapr / OBSCONV
    obs = tcoret[:,0] / OBSCONV
    uncert = tcoret[:,1] / OBSCONV
    for kk in range(navg):
        ds['avgker'].values[:,kk] = ds['avgker'].values[:,kk] / OBSCONV

    ds['avgker'].attrs['units'] = OBSUNIT + ' / ' + PROUNIT

    ds = ds.assign(priorobs=('nsound', priorobs, {'units':OBSUNIT,
        'long_name':'prior obs', 'comment':'# cm^-2 / '+str(OBSCONV)}))
    ds = ds.assign(obs=('nsound', obs, {'units':OBSUNIT,
        'long_name':'obs value', 'comment':'# cm^-2 / '+str(OBSCONV)}))
    ds = ds.assign(uncert=('nsound', uncert, {'units':OBSUNIT,
        'long_name':'obs uncertainty', 'comment':'# cm^-2 / '+str(OBSCONV)}))

    # Assign quality flags
    qc5 = dsdata['RetrievalAnomalyDiagnostic'].values
    tsurf = dsdata['RetrievedSurfaceTemperature'].values
    dfs = dsdata['DegreesofFreedomforSignal'].values
    sza = dsdata['SolarZenithAngle'].values
    isbad = (np.sum(qc5, axis=1) + (tcoret[:,1] <= 0) + (TSMAX < tsurf[:,1])
        + (dfs < DFSMIN))
    if (radtype[0].upper() == 'N'): isbad = isbad + (NIRSZA < sza)

    ds = ds.assign(isbad=('nsound', isbad, {'units':'none',
        'long_name':'obs flagged as bad?'}))

    # Assign pressure edges
    psurf = dsdata['SurfacePressure'].values
    peavg = np.zeros((nsound,NEDGE), dtype=psurf.dtype)
    peavg[:,0] = psurf
    for kk in range(1,NEDGE-1):
        peavg[:,kk] = 1000. - (kk - 1)*100.
        peavg[:,kk] = np.minimum(peavg[:,kk], psurf)
    peavg[:,NEDGE-1] = 26.

    ds = ds.assign(nedge=('nedge', np.arange(NEDGE, dtype=FILLINT.dtype),
        {'units':'#', 'long_name':'vertical grid edge number'}))
    ds = ds.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    # Assign prior profile
    scoapr = dsdata['APrioriCOSurfaceMixingRatio'].values
    pcoapr = dsdata['APrioriCOMixingRatioProfile'].values
    priorpro = np.zeros((nsound,navg), dtype=scoapr.dtype)

    for nn in range(nsound):
        ksurf = np.argmax(peavg[nn,:] < psurf[nn])
        ## Fill layers up to surface w/ surface value
        for kk in range(ksurf):
            priorpro[nn,kk] = scoapr[nn,1]
        ## Fill layers above surface w/ profile values
        for kk in range(ksurf,navg):
            priorpro[nn,kk] = pcoapr[nn,kk-1,1]

    ## Convert prior profile from ppb to log10(mol/mol)
    priorpro = np.log10(priorpro) - 9.

    ds = ds.assign(priorpro=(('nsound','navg'), priorpro, {'units':PROUNIT,
        'long_name':'prior profile'}))

    # Finish up
    ds.to_netcdf(ftr)
    ds.close()
    # Safer this way, crashes other ways on some machines
    dsdata.close()

    return None
