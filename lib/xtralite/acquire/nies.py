'''
NIES (GOSAT, GOSAT-2) support for xtralite
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Notes:
# * Requires entries in ~/.netrc file like:
#   machine data2.gosat.nies.go.jp   login >>>email<<< password >>>password<<<
#   machine prdct.gosat-2.nies.go.jp login >>>email<<< password >>>password<<<
# where >>>email<<< and >>>password<<< is your account information set up at
# the given URLs.
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
#===============================================================================

from os import path
from glob import glob
from subprocess import call
from datetime import datetime, timedelta

# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

SERVE1 = 'https://data2.gosat.nies.go.jp'
SERVE2 = 'sftp://prdct.gosat-2.nies.go.jp'

varlist = ['co2-swfp', 'ch4-swfp', 'ch4-swpr', 'co2-tir', 'ch4-tir']
satlist = ['gosat', 'gosat2']
satday0 = [datetime(2009, 4, 1), datetime(2019, 3, 1)]
namelist = ['nies_' + vv for vv in varlist]

RMTAR = True		# Remove tar files?

def setup(**xlargs):
    from xtralite.acquire import default
#   from xtralite.translate.nies import translate

    # Need to move this to setup and define new dict entry
    xlargs['ftail'] = 'h5'
#   xlargs['translate'] = translate

    xlargs = default.setup(**xlargs)

    # Time-specific variables
    jdnow = xlargs['jdbeg']
    yrget = str(jdnow.year)
    if xlargs['sat'] == 'gosat':
        dget = jdnow.strftime('%Y%m')

        # Need to move this to setup and define new dict entry/ies
        if xlargs['var'] == 'co2-swfp':
            tag = 'SWIRL2CO2'
            ver = 'v2.97r' if jdnow < datetime(2020, 6, 1) else 'v2.98r'
        elif xlargs['var'] == 'ch4-swfp':
            tag = 'SWIRL2CH4'
            ver = 'v2.95r' if jdnow < datetime(2020, 6, 1) else 'v2.96r'
        elif xlargs['var'] == 'co2-tir':
            tag = 'TIRL2CO2'
            ver = 'v1.20r'
        elif xlargs['var'] == 'ch4-tir':
            tag = 'TIRL2CH4'
            ver = 'v1.20r'
        # Needs informative error message
        else:
            raise
        fget = tag + '_' + dget + '_V0' + ver[1:-1] + '.tar'
        ardir = SERVE1 + '/wgetdata/GU/' + tag + '/' + yrget

        xlargs['fhead'] = 'GOSATTFTS'

    elif xlargs['sat'] == 'gosat2':
        dget = jdnow.strftime('%Y%m%d')

        if xlargs['var'][-4:] == 'swfp':
            ver = 'v2.0r'
            ardir = 'pub/releaseData/standardProduct/FTS-2_L2/SWFP/0200/' + yrget
            if jdnow < datetime(2021, 1, 1):
                ftag = '02SWFPV0200000010'
            elif jdnow < datetime(2022, 1, 1):
                ftag = '02SWFPV0200020011'
            else:
                ftag = '02SWFPV0200020012'
        elif xlargs['var'][-4:] == 'swpr':
            ver = 'v1.7r'
            ardir = 'pub/releaseData/standardProduct/FTS-2_L2/SWPR/0107/' + yrget
            if jdnow < datetime(2021, 1, 1):
                ftag = '02SWPRV0107000007'
            elif jdnow < datetime(2022, 1, 1):
                ftag = '02SWPRV0107000008'
            else:
                ftag = '02SWPRV0107000009'
        # Currently no TIR data
        # Needs informative error message
        else:
            raise
        fget = 'GOSAT2TFTS2' + dget + '_' + ftag + '.' + xlargs['ftail']
        ardir = SERVE2 + '/' + ardir

        xlargs['fhead'] = 'GOSAT2TFTS2'

    xlargs['ver'] = ver
    xlargs['daily'] = path.join(xlargs['head'], 'nies', xlargs['var'],
        xlargs['sat'] + '_' + ver + '_daily')
    xlargs['prep'] = xlargs['daily']

    xlargs['fget'] = fget
    xlargs['ardir'] = ardir

    return xlargs

def acquire(**xlargs):
    # Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

    wgargs = xlargs.get('wgargs', None)

    # Download lite files
    xlnow = dict(xlargs)
    for nd in range(ndays):
        jdnow = xlargs['jdbeg'] + timedelta(nd)
        xlnow['jdbeg'] = jdnow
        xlnow = setup(**xlnow)

        fget = xlnow['fget']
        ardir = xlnow['ardir']

        dout = path.join(xlargs['daily'], 'Y'+str(jdnow.year))
        fout = path.join(dout, fget)
        fday = path.join(dout, xlargs['fhead'] + jdnow.strftime('%Y%m%d') +
            '_*.' + xlargs['ftail'])

        if len(glob(fday)) != 0 and not xlargs.get('repro',False):
            continue

        pout = call(['curl', '--netrc', '--create-dirs', '-C', '-',
            '-o', fout, ardir + '/' + fget])

        if xlnow['sat'] == 'gosat':
            pout = call(['tar', 'xf', fout, '--strip-components=1',
                '-C', dout])
            if RMTAR: pout = call(['rm', fout])

    return xlargs
