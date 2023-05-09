'''
ACOS (GOSAT, OCO-2, OCO-3) support for xtralite
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

from os import path
from subprocess import call
from glob import glob
from datetime import datetime, timedelta

import numpy as np
import netCDF4
# xarray has a habit of recasting dimensions
from xtralite.patches import xarray as xr

SERVE = 'https://oco2.gesdisc.eosdis.nasa.gov/data'

varlist = ['co2']
satlist = ['gosat', 'oco2', 'oco3']
satday0 = [datetime(2009, 4, 1), datetime(2014, 8, 1), datetime(2019, 8, 1)]
namelist = satlist

def setup(**xlargs):
    from .translators import acos as translate

#   Parse name into satellite, version, etc.
    name = xlargs['name']
    isat = name.rfind('_')
    if isat == -1: isat = len(name)
    sat = name[:isat]
    ver = name[isat+1:]

    sax = sat if sat != 'gosat' else 'acos'
    if len(ver) == 0:
        if sat == 'gosat': ver = 'v9r'
        if sat == 'oco2':  ver = 'v11r'
        if sat == 'oco3':  ver = 'v10.4r'

    xlargs['sat'] = sat
    xlargs['sax'] = sax
    xlargs['ver'] = ver

#   Build directory names
    head  = xlargs.get('head',  './data')
    daily = xlargs.get('daily', '*')
    prep  = xlargs.get('prep',  '*')
    chunk = xlargs.get('chunk', '*')

    if '*' in daily:
        xlargs['daily'] = head + '/acos/' + sat + '_' + ver + '_daily'
 
    chops = xlargs['daily'].rsplit('_daily', 1)
    if len(chops) == 1: chops = chops + ['']

    if '*' in prep:
        xlargs['prep'] = '_prep'.join(chops)

    if xlargs.get('codas',False) and '*' in chunk:
        chops = xlargs['daily'].rsplit('_daily', 1)
        if len(chops) == 1: chops = chops + ['']
        xlargs['chunk'] = '_chunks'.join(chops)

#   This could be set elsewhere, maybe in xtralite, unless
#   you're planning on running the chunker from this module.
    xlargs['fhead']  = sax + '_LtCO2_'
    xlargs['fhout']  = sax + '_' + ver + '_LtCO2_'
    xlargs['ftail']  = '.nc4'
    xlargs['yrdigs'] = 2
    xlargs['recdim'] = 'sounding_id'
    xlargs['tname']  = 'sounding_time'

    if sat[:5] == 'gosat': xlargs['translate']  = translate.gosat
    if sat[:3] == 'oco':   xlargs['translate']  = translate.oco

#   Set wget arguments
    wgargs = ['-r', '-np', '-nd', '-e', 'robots=off']
    if not xlargs.get('repro',False):
        wgargs = wgargs + ['-N']
    if xlargs.get('log',None) is not None:
        wgargs = wgargs + ['-nv', '-a', xlargs['log']]
    xlargs['wgargs']  = wgargs

    return xlargs

def prep(fname, sat, ver):
#   Default settings
    UNCTHR = 1.e-3					# Flag obs w/ uncertainties < UNCTR
    ANGTHR = 80.					# Flag obs w/ ANGTHR < glint angle
    QCSNOW = True					# Apply snow quality flag?
    DOFOOT = True					# Do footprint correction?
    DOGAIN = False					# Do gain correction?

#   Name-based modifications
    if sat == 'gosat':
        QCSNOW = False					# Apply snow quality flag? (GOSAT/OCO-3 don't have it)
        DOFOOT = False					# Do footprint correction?
        DOGAIN = True					# Do gain correction?
    if sat == 'oco3':
        QCSNOW = False					# Apply snow quality flag? (GOSAT/OCO-3 don't have it)
    if sat == 'oco2' and ver[:2] == 'v9':
        QCSNOW = False					# Apply snow quality flag? (OCO-2 v9  doesn't have it)

#   Diagnostic output
    print('\nPreparing as: ' + fname)
    print('---')
    print('Applying the following modifications:')

#   Read variables we need
    ncf = netCDF4.Dataset(fname, 'a')
    sids  = ncf.variables['sounding_id']
    flags = ncf.variables['xco2_quality_flag']
    uncs  = ncf.variables['xco2_uncertainty']
    xco2s = ncf.variables['xco2']

    surfts = ncf.groups['Retrieval'].variables['surface_type'][:]
    try:
        modes = ncf.groups['Sounding'].variables['operation_mode'][:]
        glint = modes  == 1
    except:
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
        print('   * Glint angles > ' + str(ANGTHR))
        gangs = ncf.groups['Sounding'].variables['glint_angle'][:]
        flags[np.logical_and(glint, ANGTHR < gangs)] = 1

    if DOGAIN:
        print('   * Gain missing value correction')
        del ncf.groups['Sounding'].variables['gain'].missing_value

    if DOFOOT:
        print('   * Cross-track flagging and error inflation')
#       Compute track ids (trids) and track+mode ids (tmids) for each sounding
        iok   = np.array(flags[:].data == 0)
        trids = (sids[:].data//10)*10
        tmids = trids*100 + np.uint64(modes.data*10 + surfts.data)

#       Throw out tracks with less than 4 good footprints and
#       include cross-track variability in uncertainty (mode specific)
        cc, ii = np.unique(trids[iok], return_inverse=True)
        dd, jj = np.unique(tmids[iok], return_inverse=True)

        numf = np.bincount(ii)
        numt = np.bincount(jj)
        avgt = np.bincount(jj, weights=xco2s[iok])/numt
        vart = np.bincount(jj, weights=(xco2s[iok] - avgt[jj])**2)/np.maximum(numt-1,1)

#       Update flags and uncertainties
        flags[iok] = np.maximum(flags[iok], np.int8(numf[ii] < 4))
        uncs[iok]  = np.sqrt(uncs[iok]**2 + vart[jj])

#   Clobber sounding id (uint64 is slow in chunker)
    print('   * Converting sounding_id to index')
    sids[:] = np.arange(1,sids[:].size+1)
    sids.units = '#'
    sids.long_name = 'Sounding number of day'
    sids.comment = ''

    ncf.close()

    print('')
    return None

def build(**xlargs):
#   Timespan
    jdbeg = xlargs.get('jdbeg', datetime(1980, 1, 1))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

#   Archive directory
    if xlargs['sat'] == 'gosat':
        ardir = ('GOSAT_TANSO_Level2/'            + xlargs['sax'].upper() +
            '_L2_Lite_FP.' + xlargs['ver'][1:])
    else:
        ardir = (xlargs['sat'].upper() + '_DATA/' + xlargs['sax'].upper() +
            '_L2_Lite_FP.' + xlargs['ver'][1:])

#   Download and prepare lite files
    wgargs = xlargs.get('wgargs', None)
    for nd in range(ndays):
        jdnow = jdbeg + timedelta(nd)
        yrnow = str(jdnow.year)
        yrget = str(jdnow.year-2000).zfill(2)
        dget = yrget + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
        fget = '*_' + dget + '_*' + xlargs['ftail']

#       Download lite files
        pout = call(['wget', '--load-cookies', path.expanduser('~/.urs_cookies'),
            '--save-cookies', path.expanduser('~/.urs_cookies'),
            '--auth-no-challenge=on', '--keep-session-cookies',
            '--content-disposition'] + wgargs +
            [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y') + '/',
            '-A', fget, '-P', xlargs['daily'] + '/Y' + yrnow])

#       Prepare files
        flist = glob(xlargs['daily'] + '/Y' + yrnow + '/' + fget)
        if len(flist) == 0: continue

#       Use newest matching input file (may be different versions)
        flite = sorted(flist, key=path.getmtime)[-1]
        fprep = flite.replace(xlargs['daily'], xlargs['prep'], 1)

#       Skip if output file exists and not reprocessing
        if path.isfile(fprep) and not xlargs.get('repro',False): continue

        pout = call(['mkdir', '-p', xlargs['prep'] + '/Y' + yrnow])
        pout = call(['cp', '-f', flite, fprep])

        prep(fprep, xlargs['sat'], xlargs['ver'])

    return xlargs
