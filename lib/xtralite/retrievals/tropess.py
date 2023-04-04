'''
TROPESS (AIRS, CrIS) support for xtralite
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

SERVE = 'https://tropess.gesdisc.eosdis.nasa.gov/data/TROPESS_Standard'

varlist = ['o3', 'co', 'ch4', 'nh3', 'pan', 'hdo']
satlist = ['airs', 'cris-s', 'cris-1']
# Ideally
#satday0 = [dtm.datetime(2002, 5, 1), dtm.datetime(2011,10, 1),
#    dtm.datetime(2017,11, 1)]
# Actually
satday0 = [dtm.datetime(2021, 1, 1), dtm.datetime(2021, 1, 1),
    dtm.datetime(2021, 1, 1)]
namelist = ['tropess_' + vv for vv in varlist]

def setup(**xlargs):
    from . import default

#   Hack for now/only ver
    xlargs['ver'] = xlargs.get('ver', 'v1f')

    xlargs = default.setup(**xlargs)

    return xlargs

def build(**xlargs):
    import sys
    from subprocess import call
    from os.path import expanduser
    from .translate.tropess import translate

#   Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

    satlo = sat.lower()

#   Set archive directory (ardir)
    if satlo[:4] == 'airs':
        ardir = 'TRPSDL2' + var.upper() + 'AIRSFS.' + ver[1]
        fhead = 'TROPESS_AIRS-Aqua_L2_Standard_' + var.upper() + '_'
    elif satlo[:6] == 'cris-s':
        ardir = 'TRPSDL2' + var.upper() + 'CRSFS.' + ver[1]
        fhead = 'TROPESS_CrIS-SNPP_L2_Standard_' + var.upper() + '_'
    elif satlo[:6] == 'cris-1':
        ardir = 'TRPSDL2' + var.upper() + 'CRS' + sat[-1] + 'FS.' + ver[1]
        fhead = 'TROPESS_CrIS-JPSS1_L2_Standard_' + var.upper() + '_'
    else:
        sys.stderr.write('*** ERROR *** Unsupported satellite (%s)\n\n' % sat)
        sys.exit(2)

    xlargs['fhead'] = fhead
    xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + ver + '.'
    xlargs['trfun'] = translate

#   Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', dtm.datetime.now())
    ndays = (jdend - jdbeg).days + 1

#   Download
    wgargs = xlargs.get('wgargs', None)
    for nd in range(ndays):
        jdnow = jdbeg + dtm.timedelta(nd)
        yrnow = str(jdnow.year)
        dget = yrnow + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
        fget = '*_' + dget + '_*' + xlargs['ftail']

        pout = call(['wget', '--load-cookies', expanduser('~/.urs_cookies'),
            '--save-cookies', expanduser('~/.urs_cookies'),
            '--auth-no-challenge=on', '--keep-session-cookies',
            '--content-disposition'] + wgargs +
            [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y') + '/',
            '-A', fget, '-P', xlargs['daily'] + '/Y' + yrnow])

    return xlargs
