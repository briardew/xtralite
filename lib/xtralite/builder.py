'''
xtralite: Acquire, prepare, and translate constituent data for assimilation
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
# * Get defaults handled in one place insteda of all over
# * Simplify beg/jdbeg/etc. handling
# * Maybe pass name to build as a required arg, i.e.,
#       def build(name, **xlargs):
#   Then hopefully you could do stuff like
#       import xtralite
#       xtralite.build('tropomi_ch4', codas=True)
# * Move getmod to here
#===============================================================================

import sys
from os import getenv
from time import sleep
from datetime import datetime, timedelta

from xtralite import acquire, chunker

def build(**xlargs):
    # Parse name to determine module
    name = xlargs.get('name', '')
    obsmod = acquire.getmod(name)
    if obsmod is None:
        sys.stderr.write('*** ERROR *** Unsupported name (%s)\n\n' % name)
        sys.stderr.write('Run `xtralite --help` to see supported names\n')
        sys.exit(2)
    xlargs['obsmod'] = obsmod

    # To save time elsewhere
    xlargs['jdbeg'] = datetime.strptime(xlargs['beg'], '%Y-%m-%d')
    xlargs['jdend'] = datetime.strptime(xlargs['end'], '%Y-%m-%d')

    xlargs = obsmod.setup(xlargs['jdbeg'], **xlargs)

    # Need to sort out defaults a little better
    xlargs['head'] = xlargs.get('head', 'data')

    # Diagnostic output
    daily = xlargs.get('daily', '*')
    prep  = xlargs.get('prep',  '*')
    chunk = xlargs.get('chunk', '*')

    print('Acquiring daily files in ' + daily)
    if prep != daily: print('Preparing files in ' + prep)
    if xlargs.get('codas',False): print('Chunking files in ' + chunk)
    print('from ' + xlargs['beg'] + ' to ' + xlargs['end'])
    print('')
    print('OMP_NUM_THREADS = ' + getenv('OMP_NUM_THREADS'))

    # Last chance to kill
    sys.stdout.write('\nIn ')
    sys.stdout.flush()
    for nn in range(5):
        sys.stdout.write(str(5-nn) + ' ')
        sys.stdout.flush()
        sleep(1)
    sys.stdout.write('\n\n')

    # Loop over variable and satellite if unspecified
    xltame = dict(xlargs)
    if xlargs.get('var','*') == '*':
        sys.stderr.write('*** WARNING *** No variable specified\n\n')
        sys.stderr.write('Looping over: ' + ', '.join(obsmod.varlist) + '\n\n')
        for var in obsmod.varlist:
            xltame['var'] = var
            build(**xltame)
        return
    if xlargs.get('sat','*') == '*':
        sys.stderr.write('*** WARNING *** No satellite specified\n\n')
        sys.stderr.write('Looping over: ' + ', '.join(obsmod.satlist) + '\n\n')
        for sat in obsmod.satlist:
            xltame['sat'] = sat
            build(**xltame)
        return

    # Cut down on time & check range is valid
    sat = xlargs.get('sat', '*')
    jdbeg = xlargs.get('jdbeg', datetime(1980, 1, 1))
    jdend = xlargs.get('jdend', datetime.now())

    for ii in range(len(obsmod.satlist)):
        if sat.lower() == obsmod.satlist[ii].lower():
            jdbeg = max(obsmod.satday0[ii], jdbeg)
    if jdend < jdbeg:
        sys.stderr.write(('*** ERROR *** Begin date (%s) later than ' +
            'end date (%s)\n') % (jdbeg.strftime('%Y-%m-%d'),
            jdend.strftime('%Y-%m-%d')))
        sys.exit(2)

    xlargs['jdbeg'] = jdbeg
    xlargs['jdend'] = jdend
    xlargs['beg'] = jdbeg.strftime('%Y-%m-%d')
    xlargs['end'] = jdend.strftime('%Y-%m-%d')

    # Build and chunk (if requested)
    ndays = (jdend - jdbeg).days + 1
    for nd in range(ndays):
        jdnow = jdbeg + timedelta(nd)

        xlargs = obsmod.setup(jdnow, **xlargs)
        xlargs = obsmod.acquire(jdnow, **xlargs)

        if xlargs.get('codas',False):
            chops = xlargs['daily'].rsplit('_daily', 1)
            if len(chops) == 1: chops = chops + ['']
            xlargs['chunk'] = '_chunks'.join(chops)

            chunker.chunk(jdnow, **xlargs)

    return xlargs
