'''
European GHG (SCIAMACHY, GOSAT, etc.) product support for xtralite
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
from subprocess import call
from datetime import datetime, timedelta

# leic(ester), uol, and ocpr are different names for same thing
modlist  = ['besd', 'wfmd', 'imap', 'ocpr', 'leic', 'uol']
varlist  = ['co2', 'ch4', 'ch4-swpr']
satlist  = ['sciam', 'gosat', 'gosat2']
satday0  = [datetime(2002,10, 1), datetime(2009, 4, 1), datetime(2019, 3, 1)]
# NRT BESD XCO2 GOSAT retrievals are retired
# IUP points to the new NRT retrievals based on FOCAL
# Leicester and IUP products are a bit of a hack since they're not explicitly
# ESA-CCI products, but whatevs
namelist = ['besd_co2_sciam', 'wfmd_co2_sciam', 'wfmd_ch4_sciam',
    'imap_ch4_sciam', 'leic_ch4_gosat', 'leic_ch4_gosat2',
    'iup_co2_gosat', 'iup_ch4_gosat', 'iup_ch4-swpr_gosat', 'iup_co2_gosat2',
    'iup_ch4_gosat2', 'iup_ch4-swpr_gosat2']

def setup(jdnow, **xlargs):
    from xtralite.acquire import default
    from xtralite.translate.euroghg import translate

    # Make everything sits in euroghg directory
    xlargs['head'] = xlargs.get('head', path.join('data', 'euroghg'))
    xlargs['ftail'] = '.nc'

    xlargs = default.setup(jdnow, **xlargs)

    var = xlargs.get('var', '*')
    if '*' not in var:
        xlargs['translate'] = lambda fin, ftr: translate(fin, ftr, var)

    return xlargs

def acquire(jdnow, **xlargs):
    # Sometimes one works and not the other; no idea why
    SERVE = 'https://data.ceda.ac.uk/neodc'
#   SERVE = 'https://dap.ceda.ac.uk/neodc'

    # Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

    modlo = mod.lower()
    varlo = var.lower()
    satlo = sat.lower()
    verlo = ver.lower()
    varup = var.upper()

    # Greedy match all SCIAMACHY abbreviations
    if satlo[:3] == 'sci': satlo = 'sciam'

    if varlo not in varlist:
        sys.stderr.write('*** ERROR *** Invalid variable: ' + var +
            'Valid variables: ' + ', '.join(varlist) + '\n')
    elif satlo not in satlist:
        sys.stderr.write('*** ERROR *** Invalid satellite: ' + sat +
            'Valid satellites: ' + ', '.join(satlist) + '\n')

    # Set version (ver) and archive directory (ardir) based on product
    if modlo == 'besd':
        # https://www.iup.uni-bremen.de/~mreuter/besd.php
        if varlo != 'co2' or satlo != 'sciam':
            sys.stderr.write('*** ERROR *** BESD retrieval only ' +
                'available for SCIAMACHY CO2\n')
            return xlargs
        if ver == '*': ver = 'v02.01.02r'
        ardir = 'esacci/ghg/data/crdp_4/SCIAMACHY/CO2_SCI_BESD/' + ver[:-1]
        fhead = 'ESACCI-GHG-L2-' + varup + '-SCIAMACHY-BESD-'

    elif modlo == 'wfmd':
        if satlo != 'sciam':
            sys.stderr.write('*** ERROR *** WFMD retrieval only ' +
                'available for SCIAMACHY\n')
            return xlargs
        if ver == '*': ver = 'v4.0r'
        ardir = ('esacci/ghg/data/crdp_4/SCIAMACHY/' + varup +
            '_SCI_WFMD/' + ver[:-1])
        fhead = 'ESACCI-GHG-L2-' + varup + '-SCIAMACHY-WFMD-'

    elif modlo == 'imap':
        if varlo != 'ch4' or satlo != 'sciam':
            sys.stderr.write('*** ERROR *** IMAP-DOAS retrieval only ' +
                ' available for SCIAMACHY CH4\n')
            return xlargs
        if ver == '*': ver = 'v7.2r'
        ardir = 'esacci/ghg/data/crdp_4/SCIAMACHY/CH4_SCI_IMAP/' + ver[:-1]
        fhead = 'ESACCI-GHG-L2-' + varup + '-SCIAMACHY-IMAP-'

    elif modlo in ['leic', 'uol', 'ocpr']:
        if varlo != 'ch4' or satlo not in ['gosat', 'gosat2']:
            sys.stderr.write('*** ERROR *** Leicester retrieval only ' +
                'available for GOSAT & GOSAT2 CH4\n')
            return xlargs
        if satlo == 'gosat':
            if ver == '*': ver = 'v9.0r'
            ardir = 'gosat/data/ch4/nceov1.0/CH4_GOS_OCPR'
            fhead = 'UoL-GHG-L2-' + varup + '-GOSAT-OCPR-'
        elif satlo == 'gosat2':
            if ver == '*': ver = 'v1.0r'
            ardir = 'gosat/data/ch4/nceov1.0/CH4_GO2_OCPR'
            fhead = 'EOCIS-GHG-L2-' + varup + '-GOSAT2-OCPR-'

    elif modlo == 'iup':
        if satlo not in ['gosat', 'gosat2']:
            sys.stderr.write('*** ERROR *** IUP retrieval only ' +
                'available for GOSAT & GOSAT2\n')
        SERVE = 'https://www.iup.uni-bremen.de/~ghguser'
        if satlo == 'gosat':
            ver = 'v3.0f'
        elif satlo == 'gosat2':
            ver = 'v3.1f'

        # Compatibility hack for proxy retrieval
        varuse = varup
        if varup == 'CH4-SWPR': varuse = 'CH4_PROXY'

        ardir = satlo + '_focal/NRT_' + ver[:-1] + '/data/' + varuse
        fhead = 'IUP-GHG-L2-' + varuse + '-' + sat.upper() + '-FOCAL-'

    # Template variables
    xlargs['daily'] = (xlargs['head'] + '/' + mod + '/' + var +
            '/' + sat + '_' + ver + '_daily')
    xlargs['fhead'] = fhead
    xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + ver + '.'

    chops = xlargs['daily'].rsplit('_daily', 1)
    if len(chops) == 1: chops = chops + ['']
    xlargs['chunk'] = '_chunks'.join(chops)

    # Download
    wgargs = xlargs.get('wgargs', None)
    yrget = jdnow.strftime('%Y')
    moget = jdnow.strftime('%m')
    dget = jdnow.strftime('%Y%m%d')
    fget = '*-' + dget + '-*' + xlargs['ftail']

    # Might be nice to switch to cURL for everything
    if modlo == 'iup':
        # Best I could do: servers and usernames are the same
        if satlo == 'gosat':
            fnrc = path.expanduser('~/.netrc-gosat')
        else:
            fnrc = path.expanduser('~/.netrc')

        outdir = path.join(xlargs['daily'], 'Y'+yrget)
        makedirs(outdir, exist_ok=True)

        fname = fhead + dget + '-' + ver[:-1] + '_NRT' + xlargs['ftail']
        pout = call(['curl', '--fail', '--netrc-file', fnrc,
            (SERVE + '/' + ardir + '/' + yrget + '/' + moget + '/' + fname),
            '--output', path.join(outdir, fname)])
    else:
        pout = call(['wget', '--no-check-certificate'] + wgargs +
            [SERVE + '/' + ardir + '/' + yrget + '/', '-A', fget,
            '-P', path.join(xlargs['daily'], 'Y'+yrget)])

    return xlargs
