'''
xtralite: Acquire, build, and prepare constituent data for assimilation
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

from xtralite import chunker
from xtralite import retrievals

def build(**xlargs):
    from subprocess import PIPE, Popen
    from time import sleep
    import datetime as dtm
    import sys

#   To save time elsewhere
    xlargs['jdbeg'] = dtm.datetime.strptime(xlargs['beg'], '%Y-%m-%d')
    xlargs['jdend'] = dtm.datetime.strptime(xlargs['end'], '%Y-%m-%d')

#   Check for NCO utilities if chunking
    if xlargs.get('codas',False):
        try:
            pout = Popen('ncks', stdout=PIPE)
        except OSError:
            sys.stderr.write('*** ERROR *** NCO executables not in $PATH\n\n')
            sys.exit(2)

    name = xlargs.get('name', '')
    obsmod = retrievals.getmod(name)
    if obsmod is None:
        sys.stderr.write('*** ERROR *** Unsupported name (%s)\n\n' % name)
        sys.stderr.write('Run `xtralite --help` to see supported names\n')
        sys.exit(2)
    xlargs['obsmod'] = obsmod

    xlargs = obsmod.setup(**xlargs)

#   Need to sort out defaults a little better
    xlargs['head'] = xlargs.get('head', './data')

#   Diagnostic output
    daily = xlargs.get('daily', '*')
    prep  = xlargs.get('prep',  '*')
    chunk = xlargs.get('chunk', '*')

    print('Building  daily files in ' + daily)
    if prep != daily: print('Preparing files in ' + prep)
    if xlargs.get('codas',False): print('Chunking files in ' + chunk)
    print('from ' + xlargs['beg'] + ' to ' + xlargs['end'])

#   Loop over variable and satellite if unspecified
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

#   Last chance to kill
    sys.stdout.write('\nIn ')
    sys.stdout.flush()
    for nn in range(5):
        sys.stdout.write(str(5-nn) + ' ')
        sys.stdout.flush()
        sleep(1)
    sys.stdout.write('\n\n')

#   Cut down on time
    sat = xlargs.get('sat', '*')
    jdbeg = xlargs.get('jdbeg', dtm.datetime(1980, 1, 1))
    jdend = xlargs.get('jdend', dtm.datetime.now())

    for ii in range(len(obsmod.satlist)):
        if sat.lower() == obsmod.satlist[ii].lower():
            jdbeg = max(obsmod.satday0[ii], jdbeg)
    if jdend < jdbeg:
        sys.stderr.write(('*** ERROR *** Begin date (%s) later than ' +
            'end date (%s)\n') % (jdbeg.strftime('%Y-%m-%d'),
            jdend.strftime('%Y-%m-%d')))
        sys.exit(2)
    ndays = (jdend - jdbeg).days + 1

#   Update arguments
    xlargs['jdbeg'] = jdbeg
    xlargs['jdend'] = jdend
    xlargs['beg'] = jdbeg.strftime('%Y-%m-%d')
    xlargs['end'] = jdend.strftime('%Y-%m-%d')

#   Build and chunk (if requested) one day at a time
    xlday = dict(xlargs)
    for nd in range(ndays):
        jdnow = jdbeg + dtm.timedelta(nd)
        xlday['jdbeg'] = jdnow
        xlday['jdend'] = jdnow
        xlday['beg'] = jdnow.strftime('%Y-%m-%d')
        xlday['end'] = jdnow.strftime('%Y-%m-%d')

        xlday = obsmod.build(**xlday)
        if xlday.get('codas',False):
            if '*' in xlday.get('chunk','*'):
                chops = xlday['daily'].rsplit('_daily', 1)
                if len(chops) == 1: chops = chops + ['']
                xlday['chunk'] = '_chunks'.join(chops)
            chunker.chunk(**xlday)

    return xlargs
