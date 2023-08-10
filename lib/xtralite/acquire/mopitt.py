'''
MOPITT support for xtralite
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

import sys
from os import path
from subprocess import call
from datetime import datetime, timedelta

VERBOSE = True
DEBUG   = True

SERVE = 'https://l5ftl01.larc.nasa.gov/ops/misrl2l3/MOPITT'
# Does this change?
JNRT = datetime(2021, 3,24)

# Cheese stands alone
VERNUM   = 9
modname  = 'mopitt'
varlist  = ['tir', 'nir']
satlist  = ['terra']
satday0  = [datetime(2000, 3, 1)]
namelist = [modname + '_' + vv for vv in varlist]

def setup(**xlargs):
    from xtralite.acquire import default
    from xtralite.translate.mopitt import translate

    xlargs['mod'] = xlargs.get('mod', modname)
    xlargs['ftail'] = '.he5'

    var = xlargs.get('var', '*')
    xlargs['fhead'] = 'MOP02' + var[0].upper() + '-'
    xlargs['translate'] = lambda fin, ftr: translate(fin, ftr, var)

    xlargs = default.setup(**xlargs)

    return xlargs

def acquire(**xlargs):
#   Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

#   Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

#   Download
    for nd in range(ndays):
        jday = jdbeg + timedelta(nd)
        yget = str(jday.year)
        dget = yget + str(jday.month).zfill(2) + str(jday.day).zfill(2)
        fget = '*-' + dget + '-*' + xlargs['ftail']

#       Determine version based on date
        vernow = 'v' + str(VERNUM) + 'r'
        if JNRT < jday: vernow = 'v' + str(100+VERNUM) + 'r'

        veruse = ver
        if ver == '*': veruse = vernow

        if veruse.lower() != vernow.lower():
            sys.stderr.write(("*** WARNING *** Specified version (%s) " +
                "doesn't match current version (%s)\n") % (veruse, vernow))
            continue

#       Archive directory (ardir)
        ardir = 'MOP02' + var[0].upper() + '.' + veruse[1:-1].zfill(3)

#       Set daily directory if unspecified and make sure prep matches
#       This should be done in setup or someting, super hokey
#       Needs to be fixed everywhere (***FIXME***)
        if '*' in xlargs['daily']:
            head = xlargs.get('head', 'data')
            xlargs['daily'] = path.join(head, mod, 
                var + '_' + veruse + '_daily')
        xlargs['prep'] = xlargs['daily']
        xlargs['fhout'] = mod + '_' + var + '_' + veruse + '.'

        cmd = (['wget', '--load-cookies', path.expanduser('~/.urs_cookies'),
            '--save-cookies', path.expanduser('~/.urs_cookies'),
            '--auth-no-challenge=on', '--keep-session-cookies',
            '--content-disposition'] + xlargs['wgargs'] +
            [SERVE + '/' + ardir + '/' + jday.strftime('%Y.%m.%d') + '/',
            '-A', fget, '-P', path.join(xlargs['daily'], 'Y'+yget)])
        if VERBOSE: print(' '.join(cmd))
        pout = call(cmd)        

    return xlargs
