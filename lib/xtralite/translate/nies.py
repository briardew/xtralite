'''
Translate NIES retrievals to CoDAS format
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
#===============================================================================

from datetime import datetime, timedelta

import numpy as np
import netCDF4
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

RECDIM = 'nsound'

def translate(fin, ftr, var, sat):
    '''Translate NIES retrievals to CoDAS format'''

    ncf = netCDF4.Dataset(fin, diskless=True, persist=False)

    if var == 'co2-swfp' and sat == 'gosat':
        ncdata = ncf['Data/mixingRatio']
        ncqual = ncf['Data/retrievalQuality']
        ncloc  = ncf['Data/geolocation']
        ncattr = ncf['scanAttribute']
        ncref  = ncf['scanAttribute/referenceData']

        ddata = xr.open_dataset(xr.backends.NetCDF4DataStore(ncdata))
        dqual = xr.open_dataset(xr.backends.NetCDF4DataStore(ncqual))
        dloc  = xr.open_dataset(xr.backends.NetCDF4DataStore(ncloc))
        dattr = xr.open_dataset(xr.backends.NetCDF4DataStore(ncattr))
        dref  = xr.open_dataset(xr.backends.NetCDF4DataStore(ncref))

        # Compatability hack (***FIXME***)
        ddata = ddata.rename({'phony_dim_18':RECDIM})
        dqual = dqual.rename({'phony_dim_19':RECDIM, 'phony_dim_20':'navg'})
        dloc  =  dloc.rename({'phony_dim_14':RECDIM})
        dref  =  dref.rename({'phony_dim_60':RECDIM, 'phony_dim_61':'navg'})

        dd = ddata[['XCO2BiasCorrected', 'XCO2BiasCorrectedError']]
        dd = dd.assign(dqual[['columnAveragingKernel']])
        dd = dd.assign(dloc[[ 'latitude', 'longitude']])
        dd = dd.assign(dref[[ 'CO2Profile']])
        dd = dd.rename({'latitude':'lat', 'longitude':'lon',
            'XCO2BiasCorrected':'obs', 'XCO2BiasCorrectedError':'uncert',
            'columnAveragingKernel':'avgker', 'CO2Profile':'priorpro'})

    elif var == 'co2-swfp' and sat == 'gosat2':
       ncdata = ncf['RetrievalResult']
       ncloc  = ncf['SoundingGeometry']
       ncattr = ncf['SoundingAttribute']
    elif var == 'co2-swfp' and sat == 'gosat2':
        dd = ddata[['APrioriCOTotalColumn', 'TotalColumnAveragingKernel']]
        dd = dd.assign(dloc[['Latitude', 'Longitude']])
        dd = dd.rename({'nTime':'nsound', 'nPrs2':'navg', 'Latitude':'lat',
            'Longitude':'lon', 'APrioriCOTotalColumn':'priorobs',
            'TotalColumnAveragingKernel':'avgker'})

    inan = np.isnan(dd['avgker'].values)
    dd['avgker'].values[inan] = 0.

    # Dimension sizes needed below
    nsound = dd.sizes['nsound']
    navg   = dd.sizes['navg']

    # Assign date and time
    year  = dattr.attrs['Year']
    month = dattr.attrs['Month']
    day   = dattr.attrs['Day']
    secs  = dloc['SecondsinDay'].values

    date = np.zeros(nsound, dtype=FILLINT.dtype)
    time = np.zeros(nsound, dtype=FILLINT.dtype)

    for nn in range(nsound):
        tt = datetime(year,month,day) + timedelta(seconds=int(secs[nn]))
        date[nn] = tt.day    + tt.month*100  + tt.year*10000
        time[nn] = tt.second + tt.minute*100 + tt.hour*10000

    inan = np.isnan(secs)
    date[inan] = FILLINT
    time[inan] = FILLINT

    dd = dd.assign(date=('nsound', date, {'units':'YYYYMMDD',
        'long_name':'sounding date', '_FillValue':FILLINT}))
    dd = dd.assign(time=('nsound', time, {'units':'hhmmss',
        'long_name':'sounding date', '_FillValue':FILLINT}))

    # Assign prior obs, obs, and uncert
    tcoapr = ddata['APrioriCOTotalColumn'].values
    tcoret = ddata['RetrievedCOTotalColumn'].values
    drycol = ddata['DryAirColumn'].values

    ## Convert from #/cm^2 to mol/m^2
    priorobs = tcoapr / OBSCONV
    obs = tcoret[:,0] / OBSCONV
    uncert = tcoret[:,1] / OBSCONV
    for kk in range(navg):
        dd['avgker'].values[:,kk] = dd['avgker'].values[:,kk] / OBSCONV

    dd['avgker'].attrs['units'] = OBSUNIT + ' / ' + PROUNIT

    dd = dd.assign(priorobs=('nsound', priorobs, {'units':OBSUNIT,
        'long_name':'prior obs', 'comment':'# cm^-2 / '+str(OBSCONV)}))
    dd = dd.assign(obs=('nsound', obs, {'units':OBSUNIT,
        'long_name':'obs value', 'comment':'# cm^-2 / '+str(OBSCONV)}))
    dd = dd.assign(uncert=('nsound', uncert, {'units':OBSUNIT,
        'long_name':'obs uncertainty', 'comment':'# cm^-2 / '+str(OBSCONV)}))

    # Assign quality flags
    qc5 = ddata['RetrievalAnomalyDiagnostic'].values
    tsurf = ddata['RetrievedSurfaceTemperature'].values
    dfs = ddata['DegreesofFreedomforSignal'].values
    sza = ddata['SolarZenithAngle'].values
    isbad = (np.sum(qc5, axis=1) + (tcoret[:,1] <= 0) + (TSMAX < tsurf[:,1])
        + (dfs < DFSMIN))
    if (radtype[0].upper() == 'N'): isbad = isbad + (NIRSZA < sza)

    dd = dd.assign(isbad=('nsound', isbad, {'units':'none',
        'long_name':'obs flagged as bad?'}))

    # Assign pressure edges
    psurf = ddata['SurfacePressure'].values
    peavg = np.zeros((nsound,NEDGE), dtype=psurf.dtype)
    peavg[:,0] = psurf
    for kk in range(1,NEDGE-1):
        peavg[:,kk] = 1000. - (kk - 1)*100.
        peavg[:,kk] = np.minimum(peavg[:,kk], psurf)
    peavg[:,NEDGE-1] = 26.

    dd = dd.assign(nedge=('nedge', np.arange(NEDGE, dtype=FILLINT.dtype),
        {'units':'#', 'long_name':'vertical grid edge number'}))
    dd = dd.assign(peavg=(('nsound','nedge'), peavg, {'units':'hPa',
        'long_name':'pressure edges'}))

    # Assign prior profile
    scoapr = ddata['APrioriCOSurfaceMixingRatio'].values
    pcoapr = ddata['APrioriCOMixingRatioProfile'].values
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

    dd = dd.assign(priorpro=(('nsound','navg'), priorpro, {'units':PROUNIT,
        'long_name':'prior profile'}))

    # Finish up
    dd.to_netcdf(ftr)
    dd.close()
    # Safer this way, crashes other ways on some machines
    ddata.close()

    return None
