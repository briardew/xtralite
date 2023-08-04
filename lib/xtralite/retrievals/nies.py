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
from subprocess import call
from datetime import datetime, timedelta

# stop xarray from recasting coordinates
# xarray has a habit of recasting dimensions
from xtralite.patches import xarray as xr

SERVE1 = 'https://data2.gosat.nies.go.jp'
SERVE2 = 'sftp://prdct.gosat-2.nies.go.jp'

varlist = ['co2-swfp', 'ch4-swfp', 'ch4-swpr', 'co2-tir', 'ch4-tir']
satlist = ['gosat', 'gosat2']
satday0 = [datetime(2009, 4, 1), datetime(2019, 3, 1)]
namelist = ['nies_' + vv for vv in varlist]

def setup(**xlargs):
    from xtralite.retrievals import default
#   from xtralite.translators import nies as translate

#   xlargs['translate'] = translate
    xlargs = default.setup(**xlargs)

    return xlargs

def acquire(**xlargs):
    # Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

    wgargs = xlargs.get('wgargs', None)

    # Download lite files
    if xlargs['sat'] == 'gosat':
        for nd in range(ndays):
            jdnow = jdbeg + timedelta(nd)
            yrget = str(jdnow.year)
            dget = jdnow.strftime('%Y%m')

            # Could move this to setup and define new dict entry
            if xlargs['var'] == 'co2-swfp':
                ardir = 'wgetdata/GU/SWIRL2CO2/' + yrget
                if jdnow < datetime(2020, 6, 1):
                    ver = 'v2.97r'
                    fget = 'SWIRL2CO2_' + dget + '_V02.97.tar'
                else:
                    ver = 'v2.98r'
                    fget = 'SWIRL2CO2_' + dget + '_V02.98.tar'
            elif xlargs['var'] == 'ch4-swfp':
                ardir = 'wgetdata/GU/SWIRL2CH4/' + yrget
                if jdnow < datetime(2020, 6, 1):
                    ver = 'v2.95r'
                    fget = 'SWIRL2CH4_' + dget + '_V02.95.tar'
                else:
                    ver = 'v2.96r'
                    fget = 'SWIRL2CH4_' + dget + '_V02.96.tar'
            elif xlargs['var'] == 'co2-tir':
                ardir = 'wgetdata/GU/TIRL2CO2/' + yrget
                ver = 'v1.20r'
                fget = 'TIRL2CO2_' + dget + '_V01.20.tar'
            elif xlargs['var'] == 'ch4-tir':
                ardir = 'wgetdata/GU/TIRL2CH4/' + yrget
                ver = 'v1.20r'
                fget = 'TIRL2CH4_' + dget + '_V01.20.tar'
            # Needs informative error message
            else:
                raise

            fout = path.join(xlargs['head'], 'nies', 'gosat_' + ver +
                '_daily', 'Y'+yrget, fget)
            pout = call(['curl', '--netrc', '--create-dirs', '-C', '-',
                '-o', fout, SERVE1 + '/' + ardir + '/' + fget])
#           pout = call(['tar', 'xf', fget])

    elif xlargs['sat'] == 'gosat2':
        for nd in range(ndays):
            jdnow = jdbeg + timedelta(nd)
            yrget = str(jdnow.year)
            dget = jdnow.strftime('%Y%m%d')

            # Could move this to setup and define new dict entry
            xlargs['ftail'] = 'h5'
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
            fout = path.join(xlargs['head'], 'nies', 'gosat2_' + ver +
                '_daily', 'Y'+yrget, fget)

            pout = call(['curl', '--netrc', '--create-dirs', '-C', '-',
                '-o', fout, SERVE2 + '/' + ardir + '/' + fget])

    # Needs informative error message
    else:
        raise

    return xlargs
