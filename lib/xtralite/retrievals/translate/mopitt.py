'''
Translate MOPITT retrievals to xtralite
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

NEDGE = 11

DFSMIN = 0.25			# Minimum degrees-of-freedom (#)
TSMAX  = 320			# Maximum surface temperature (K)
NIRSZA = 60			# Maximum NIR solar zenith angle (deg)

def translate(fin, ftr, radtype):
    '''Translate MOPITT retrievals to xtralite'''

    ncf = netCDF4.Dataset(fin, diskless=True, persist=False)
    ncdata = ncf['HDFEOS/SWATHS/MOP02/Data Fields']
    ncloc  = ncf['HDFEOS/SWATHS/MOP02/Geolocation Fields']
    ncattr = ncf['HDFEOS/ADDITIONAL/FILE_ATTRIBUTES']

    dsdata = xr.open_dataset(xr.backends.NetCDF4DataStore(ncdata))
    dsloc  = xr.open_dataset(xr.backends.NetCDF4DataStore(ncloc))
    dsattr = xr.open_dataset(xr.backends.NetCDF4DataStore(ncattr))

#   Copy and rename variables w/ appropriate dimensions
    ds = dsdata[['APrioriCOTotalColumn', 'TotalColumnAveragingKernel']]
    ds = ds.assign(dsloc[['Latitude', 'Longitude']])
    ds = ds.rename({'nTime':'nsound', 'nPrs2':'navg', 'Latitude':'lat',
        'Longitude':'lon', 'APrioriCOTotalColumn':'priorobs',
        'TotalColumnAveragingKernel':'avgker'})

#   Switch avgker nans to zeros
    inan = np.isnan(ds['avgker'].values)
    ds['avgker'].values[inan] = 0.

#   Dimension sizes needed below
    nsound = ds.sizes['nsound']
    navg   = ds.sizes['navg']

#   Build date and time
#   -------------------
    year  = dsattr.attrs['Year']
    month = dsattr.attrs['Month']
    day   = dsattr.attrs['Day']
    secs  = dsloc['SecondsinDay'].values

    date = np.zeros(nsound, dtype='int32')
    time = np.zeros(nsound, dtype='int32')

    for nn in range(nsound):
        tt = dtm.datetime(year,month,day) + dtm.timedelta(seconds=int(secs[nn]))
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    ds = ds.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', 'missing_value':np.int32(-9999)}))
    ds = ds.assign(time=('nsound', time, {'units':'YYYYMMDD',
        'long_name':'sounding date', 'missing_value':np.int32(-9999)}))

#   Build prior obs, obs, and uncert
#   --------------------------------
    tcoapr = dsdata['APrioriCOTotalColumn'].values
    tcoret = dsdata['RetrievedCOTotalColumn'].values
    drycol = dsdata['DryAirColumn'].values

#   Convert from #/cm^2 to ppb
    priorobs = tcoapr / drycol * 1.e9
    obs = tcoret[:,0] / drycol * 1.e9
    uncert = tcoret[:,1] / drycol * 1.e9

    ds['avgker'].attrs['units'] = 'ppb / log10(VMR)'
    for kk in range(navg):
        ds['avgker'].values[:,kk] = ds['avgker'].values[:,kk] / drycol * 1.e9

    ds = ds.assign(priorobs=(('nsound',), priorobs, {'units':'ppb',
        'long_name':'prior obs'}))
    ds = ds.assign(obs=(('nsound',), obs, {'units':'ppb',
        'long_name':'obs value'}))
    ds = ds.assign(uncert=(('nsound',), uncert, {'units':'ppb',
        'long_name':'obs uncertainty'}))

#   Build quality flags
#   -------------------
    qc5 = dsdata['RetrievalAnomalyDiagnostic'].values
    tsurf = dsdata['RetrievedSurfaceTemperature'].values
    dfs = dsdata['DegreesofFreedomforSignal'].values
    sza = dsdata['SolarZenithAngle'].values
    isbad = (np.sum(qc5, axis=1) + (tcoret[:,1] <= 0) + (TSMAX < tsurf[:,1])
        + (dfs < DFSMIN))
    if (radtype[0].upper() == 'N'): isbad = isbad + (NIRSZA < sza)

    ds = ds.assign(isbad=(('nsound',), isbad, {'units':'none',
        'long_name':'obs flagged as bad?'}))

#   Build pressure edges
#   --------------------
    psurf = dsdata['SurfacePressure'].values
    peavg = np.zeros((nsound,NEDGE), dtype=psurf.dtype)
    peavg[:,0] = psurf
    for kk in range(1,NEDGE-1):
        peavg[:,kk] = 1000. - (kk - 1)*100.
        peavg[:,kk] = np.minimum(peavg[:,kk], psurf)
    peavg[:,NEDGE-1] = 26.

    ds = ds.assign(nedge=('nedge', np.arange(NEDGE, dtype='int32')))
    ds = ds.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

#   Build prior profile
#   -------------------
    scoapr = dsdata['APrioriCOSurfaceMixingRatio'].values
    pcoapr = dsdata['APrioriCOMixingRatioProfile'].values
    priorpro = np.zeros((nsound,navg), dtype=scoapr.dtype)

    for nn in range(nsound):
        ksurf = np.argmax(peavg[nn,:] < psurf[nn])
#       Fill layers up to surface w/ surface value
        for kk in range(ksurf):
            priorpro[nn,kk] = scoapr[nn,1]
#       Fill layers above surface w/ profile values
        for kk in range(ksurf,navg):
            priorpro[nn,kk] = pcoapr[nn,kk-1,1]

#   Convert from ppb to log10(VMR)
    priorpro = np.log10(priorpro) - 9.

    ds = ds.assign(priorpro=(('nsound','navg'), priorpro, {'units':'log10(VMR)',
        'long_name':'prior profile'}))

    ds.to_netcdf(ftr)
    ds.close()

    dsdata.close()
#   Only need to close one?
#   dsloc.close()
#   dsattr.close()

    return None
