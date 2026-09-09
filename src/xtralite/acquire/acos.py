'''
ACOS (GOSAT, OCO-2, OCO-3) support for xtralite
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

import sys
from os import path, makedirs
from shutil import copy
from glob import glob
from datetime import datetime
from time import sleep
import earthaccess
import requests
import numpy as np
import netCDF4


varlist = ['co2']
satlist = ['gosat', 'oco2', 'oco3']
satday0 = [datetime(2009, 4, 1), datetime(2014, 8, 1), datetime(2019, 8, 1)]
namelist = [ss for ss in satlist]

passexs = (
    requests.exceptions.HTTPError,
    requests.exceptions.ReadTimeout,
)


def setup(jdnow, **xlargs):
    from xtralite.translate import acos as translate

    # Parse name into satellite, version, etc.
    name = xlargs['name']
    isat = name.rfind('_')
    if isat == -1: isat = len(name)
    sat = name[:isat].lower().replace('-', '')
    ver = name[isat+1:]

    # Extra work to handle naming differences
    sax = sat if sat != 'gosat' else 'acos'

    # Apply default version if unspecified
    if len(ver) == 0:
        if sat == 'gosat': ver = 'v11'
        if sat == 'oco2':  ver = 'v11.2r'
        if sat == 'oco3':  ver = 'v11r'

    xlargs['sat'] = sat
    xlargs['sax'] = sax
    xlargs['ver'] = ver

    # Build directory names
    head  = xlargs.get('head',  'data')
    daily = xlargs.get('daily', '*')
    prep  = xlargs.get('prep',  '*')
    chunk = xlargs.get('chunk', '*')

    if '*' in daily:
        xlargs['daily'] = path.join(head, 'acos', f'{sat}_{ver}_daily')
 
    chops = xlargs['daily'].rsplit('_daily', 1)
    if len(chops) == 1: chops = chops + ['']

    if '*' in prep:
        xlargs['prep'] = '_prep'.join(chops)

    if xlargs.get('codas',False) and '*' in chunk:
        chops = xlargs['daily'].rsplit('_daily', 1)
        if len(chops) == 1: chops = chops + ['']
        xlargs['chunk'] = '_chunks'.join(chops)

    # OCO-2 v##.# denotes the FORWARD stream, while v##.#r is REPROCESSED
    # ACOS v##.# denotes the REPROCESSED stream
    ptag = 'LtCO2' if ver[-1] == 'r' or sax == 'acos' else 'FwCO2'
    xlargs['fhead']  = f'{sax}_{ptag}_'
    xlargs['fhout']  = f'{sax}_{ver}_{ptag}_'
    xlargs['ftail']  = '.nc4'
    xlargs['ftout']  = '.nc4'
    xlargs['yrdigs'] = 2
    xlargs['recdim'] = 'sounding_id'
    xlargs['tname']  = 'sounding_time'

    if sat[:5] == 'gosat': xlargs['translate']  = translate.gosat
    if sat[:3] == 'oco':   xlargs['translate']  = translate.oco

    return xlargs


def prep(fname, sat, ver):
    # Default settings
    UNCTHR = 1.e-3					# Flag obs w/ uncertainties < UNCTR
    ANGTHR = 80.					# Flag obs w/ ANGTHR < solar + sensor zenith angle
    QCSNOW = True					# Apply snow quality flag?
    DOFOOT = True					# Do footprint correction?
    DOGAIN = False					# Do gain correction?

    # Name-based modifications
    if sat == 'gosat':
        QCSNOW = False					# Apply snow quality flag? (GOSAT/OCO-3 don't have it)
        DOFOOT = False					# Do footprint correction?
        DOGAIN = True					# Do gain correction?
    elif sat == 'oco3':
        QCSNOW = False					# Apply snow quality flag? (GOSAT/OCO-3 don't have it)
    elif sat == 'oco2' and ver[:2] == 'v9':
        QCSNOW = False					# Apply snow quality flag? (OCO-2 v9    don't have it)

    if ver[-1] == 'f':
        DOFOOT = False					# Do footprint correction?

    # Diagnostic output
    print('\nPreparing as: ' + fname)
    print('---')
    print('Applying the following modifications:')

    # Read variables we need
    ncf = netCDF4.Dataset(fname, 'a')
    sids  = ncf.variables['sounding_id']
    flags = ncf.variables['xco2_quality_flag']
    uncs  = ncf.variables['xco2_uncertainty']
    xco2s = ncf.variables['xco2']

    surfts = ncf.groups['Retrieval'].variables['surface_type'][:]
    try:
        modes = ncf.groups['Sounding'].variables['operation_mode'][:]
        glint = modes  == 1
    except Exception:
        glint = surfts == 0

    ibad = np.logical_and(uncs[:] < UNCTHR, flags[:] == 0)
    sbad = sids[ibad]
    for ss in sbad: print('   * Uncertainty flag for sounding #' + str(ss))
    flags[ibad] = 1

    if QCSNOW:
        print('   * Snow/ice quality flag')
        flins = ncf.groups['Retrieval'].variables['snow_flag'][:]
        flags[:] = np.maximum(flags[:], flins)

    if ANGTHR < 90:
        print('   * Total zenith angle > ' + str(ANGTHR))
        zangs = (ncf.variables['solar_zenith_angle'][:] +
            ncf.variables['sensor_zenith_angle'][:])
        flags[np.logical_and(glint, ANGTHR < zangs)] = 1

    if DOGAIN:
        print('   * Gain missing value correction')
        del ncf.groups['Sounding'].variables['gain'].missing_value

    if DOFOOT:
        print('   * Cross-track flagging and error inflation')
        # Compute track ids (trids) and track+mode ids (tmids) for each sounding
        iok   = np.array(flags[:].data == 0)
        trids = (sids[:].data//10)*10
        tmids = trids*100 + np.uint64(modes.data*10 + surfts.data)

        # Throw out tracks with less than 4 good footprints and
        # include cross-track variability in uncertainty (mode specific)
        cc, ii = np.unique(trids[iok], return_inverse=True)
        dd, jj = np.unique(tmids[iok], return_inverse=True)

        numf = np.bincount(ii)
        numt = np.bincount(jj)
        avgt = np.bincount(jj, weights=xco2s[iok])/numt
        vart = np.bincount(jj, weights=(xco2s[iok] - avgt[jj])**2)/np.maximum(numt-1,1)

        # Update flags and uncertainties
        flags[iok] = np.maximum(flags[iok], np.int8(numf[ii] < 4))
        uncs[iok]  = np.sqrt(uncs[iok]**2 + vart[jj])

    # Clobber sounding id (uint64 is slow in chunker)
    print('   * Converting sounding_id to index')
    sids[:] = np.arange(1,sids[:].size+1)
    sids.units = '#'
    sids.long_name = 'Sounding number of day'
    sids.comment = ''

    ncf.close()

    print('')
    return None


def acquire(jdnow, **xlargs):
    xlnow = setup(jdnow, **xlargs)

    ver = xlnow.get('ver', '')
    sax = xlnow.get('sax', '')

    # Download and prepare lite files
    yrnow = str(jdnow.year)
    yrget = str(jdnow.year-2000).zfill(2)
    dget = yrget + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    fget = xlnow['fhead'] + dget + '_*' + xlnow['ftail']
    dirget = path.join(xlargs['daily'], f'Y{yrnow}')

    # OCO-2 v##.# denotes the FORWARD stream, while v##.#r is REPROCESSED
    # ACOS v##.# denotes the REPROCESSED stream
    stream = 'Lite' if ver[-1] == 'r' or sax == 'acos' else 'Fwd'
    shorty = f'{sax.upper()}_L2_{stream}_FP'
    granny = xlnow['fhead'] + dget + '_*'
    verget = ver[1:]
    # Special treatement for ACOS to allow for ver = 11r, 11.0, etc.
    if sax == 'acos':
        if verget[-1] == 'r': verget = verget[:-1]
        if '.' not in verget: verget = verget + '.0'

    # Wrap download in a few tries in case of connection issues
    MAXTRIES = 10
    SLEEPLEN = 60
    for nn in range(MAXTRIES):
        try:
            earthaccess.login(strategy='netrc')
            results = earthaccess.search_data(short_name=shorty, version=verget,
                granule_name=granny)
            urls = []
            for rr in results:
                urls += rr.data_links()

            if len(urls) == 0:
                return xlnow

            # This croaks (because of parallelism?), resort to requests instead below
            # files = earthaccess.download(urls, dirget)
            break
        except passexs as e:
            print(f'{type(e).__name__}: {e}', file=sys.stderr)
        except Exception:
            raise

        sleep(SLEEPLEN)

    # Use requests for download since earthaccess croaks
    makedirs(dirget, exist_ok=True)
    files = [path.join(dirget, url.split('/')[-1]) for url in urls]
    with requests.Session() as ss:
        for url, file in zip(urls, files):
            for nn in range(MAXTRIES):
                try:
                    if not path.isfile(file) or xlnow['repro']:
                        response = ss.get(url, stream=True)
                        response.raise_for_status()
                        with open(file, 'wb') as fid:
                            fid.write(response.content)
                    break
                except passexs as e:
                    print(f'{type(e).__name__}: {e}', file=sys.stderr)
                except Exception:
                    raise

                sleep(SLEEPLEN)

    # Prepare files
    flist = glob(path.join(dirget, fget))
    if len(flist) == 0:
        return xlnow

    # Use newest matching input file (may be different versions)
    flite = sorted(flist, key=path.getmtime)[-1]
    fprep = flite.replace(xlnow['daily'], xlnow['prep'], 1)

    # Skip if output file exists and not reprocessing
    if path.isfile(fprep) and not xlnow['repro']:
        return xlnow

    makedirs(path.join(xlnow['prep'], f'Y{yrnow}'), exist_ok=True)
    copy(flite, fprep)

    prep(fprep, xlnow['sat'], ver)

    return xlnow
