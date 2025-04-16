'''
MOPITT support for xtralite
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
# * This version still cannot take a version string, e.g., mopitt_tir_v7
# * This version still will choke if var is *
#===============================================================================

import sys
from os import path
from subprocess import call
from datetime import datetime, timedelta

VERBOSE = True
DEBUG   = True

VNUMDEF  = 9
VERDEF   = 'v' + str(VNUMDEF) + 'r'
modname  = 'mopitt'
varlist  = ['tir', 'nir']
satlist  = ['terra']
satday0  = [datetime(2000, 3, 1)]
namelist = [modname + '_' + vv for vv in varlist]

# This value changes: lags present by about a year
JDNRT = datetime(2023,11,25)

SERVE = 'https://l5ftl01.larc.nasa.gov/ops/misrl2l3/MOPITT'

def setup(jdnow, **xlargs):
    from xtralite.acquire import default
    from xtralite.translate.mopitt import translate

    mod = modname
    sat = satlist[0]

    xlargs['mod'] = mod
    xlargs['sat'] = sat
    xlargs['ftail'] = '.he5'

    xlargs = default.setup(jdnow, **xlargs)

    # Fill unspecified version with default and
    # flip to forward stream based on date
    ver = xlargs['ver']
    if ver == '*': ver = VERDEF
    if ver == VERDEF and JDNRT <= jdnow: ver = 'v' + str(100+VNUMDEF) + 'f'
    xlargs['ver'] = ver

    # Fill directory and filename templates (needs improvement)
    var  = xlargs['var']
    head = xlargs['head']

    daily = path.join(head, mod, var + '_' + ver + '_daily')
    chunk = path.join(head, mod, var + '_' + ver + '_chunks')
    xlargs['daily'] = daily
    xlargs['prep']  = daily
    xlargs['chunk'] = chunk

    xlargs['fhout'] = mod + '_' + var + '_' + ver + '.'
    xlargs['fhead'] = 'MOP02' + var[0].upper() + '-'
    xlargs['translate'] = lambda fin, ftr: translate(fin, ftr, var)

    return xlargs

# What if it were just called like
# import mopitt
# mopitt.acquire(datetime(2020, 1, 1), 'mopitt_terra_tir')
#
# import euroghg
# euroghg.acquire(datetime(2020, 1, 1), 'leic_ch4_v9')
def acquire(jdnow, **xlargs):
    xlargs = setup(jdnow, **xlargs)
    ver = xlargs['ver']
    var = xlargs['var']

    # Download
    year = str(jdnow.year)
    date = year + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    fwild = '*-' + date + '-*' + xlargs['ftail']
    ardir = 'MOP02' + var[0].upper() + '.' + ver[1:-1].zfill(3)

    cmd = (['wget', '--load-cookies', path.expanduser('~/.urs_cookies'),
        '--save-cookies', path.expanduser('~/.urs_cookies'),
        '--auth-no-challenge=on', '--keep-session-cookies',
        '--content-disposition'] + xlargs['wgargs'] +
        [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y.%m.%d') + '/',
        '-A', fwild, '-P', path.join(xlargs['daily'], 'Y'+year)])
    if VERBOSE: print(' '.join(cmd))
    pout = call(cmd)        

    return xlargs
