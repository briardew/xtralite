'''
MOPITT support for xtralite
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
import sys
from . import default

VERBOSE = True
DEBUG   = True

SERVE = 'https://l5ftl01.larc.nasa.gov/ops/misrl2l3/MOPITT'
# Does this change?
JLAST = dtm.datetime(2021, 3,24)

# Cheese stands alone
VERNUM   = 9
modname  = 'mopitt'
varlist  = ['tir', 'nir']
satlist  = ['terra']
satday0  = [dtm.datetime(2000, 3, 1)]
namelist = [modname + '_' + vv for vv in varlist]

def setup(**xlargs):
#   Fill keys with only one possible value
    xlargs['mod'] = xlargs.get('mod', modname)
    xlargs['ftail'] = xlargs.get('ftail', '.he5')

    xlargs = default.setup(**xlargs)

    return xlargs

def build(**xlargs):
    from subprocess import call
    from os.path import expanduser

#   default.build(varlist, satlist, satday0, __self__, **xltmps)

#   Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

#   Loop over variable and satellite if unspecified
    if var == '*':
        sys.stderr.write('*** WARNING *** No variable specified in name\n\n')
        sys.stderr.write('Looping over ' + ', '.join(varlist) + '\n\n')
        for var in varlist:
            xlargs['var'] = var
            build(**xlargs)
        return
    if sat == '*':
        sys.stderr.write('*** WARNING *** No satellite specified in name\n\n')
        sys.stderr.write('Looping over ' + ', '.join(satlist) + '\n\n')
        for sat in satlist:
            xlargs['sat'] = sat
            build(**xlargs)
        return

#   Determine timespan
    jday0 = xlargs.get('day0', dtm.datetime(1980, 1, 1))
    jdayF = xlargs.get('dayF', dtm.datetime.now())

#   Cut down on time
    for ii in range(len(satlist)):
        if sat.lower() == satlist[ii].lower(): jday0 = max(satday0[ii], jday0)
    if jdayF < jday0:
        sys.stderr.write(('*** ERROR *** End date (%s) earlier than ' +
            'earliest start date (%s)\n') % (jday0.strftime('%Y-%m-%d'),
            jdayF.strftime('%Y-%m-%d')))
        sys.exit(2)

#   Download
    jday0 = xlargs.get('day0', dtm.datetime(1980, 1, 1))
    jdayF = xlargs.get('dayF', dtm.datetime.now())
    ndays = (jdayF - jday0).days + 1
    for nd in range(ndays):
        jday = jday0 + dtm.timedelta(nd)
        yget = str(jday.year)
        dget = yget + str(jday.month).zfill(2) + str(jday.day).zfill(2)
        fget = '*-' + dget + '-*' + xlargs['ftail']

#       Determine version based on date
        vernow = 'v' + str(VERNUM) + 'r'
        if JLAST < jday: vernow = 'v' + str(100+VERNUM) + 'r'

        veruse = ver
        if ver == '*': veruse = vernow

        if veruse.lower() != vernow.lower():
            sys.stderr.write('*** WARNING *** Specified version (%s) ' +
                'does not match current version (%s)\n' % (veruse, vernow))
            continue

#       Archive directory (ardir)
        ardir = 'MOP02' + sat[0].upper() + '.' + veruse[1:-1].zfill(3)

        if '*' in xlargs['daily']:
            xlargs['daily'] = ('./data/' + mod + '/' + 
                var + '_' + veruse + '_daily')

        cmd = (['wget', '--load-cookies', expanduser('~/.urs_cookies'),
            '--save-cookies', expanduser('~/.urs_cookies'),
            '--auth-no-challenge=on', '--keep-session-cookies',
            '--content-disposition'] + xlargs['wgargs'] +
            [SERVE + '/' + ardir + '/' + jday.strftime('%Y.%m.%d') + '/',
            '-A', fget, '-P', xlargs['daily'] + '/Y' + yget])
        if VERBOSE: print(' '.join(cmd))
        pout = call(cmd)        
