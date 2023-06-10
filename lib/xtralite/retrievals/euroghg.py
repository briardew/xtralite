'''
European GHG (SCIAMACHY, GOSAT, etc.) product support for xtralite
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

import sys
from subprocess import call
from datetime import datetime, timedelta

# I think the former is a link to the latter
#SERVE = 'https://data.ceda.ac.uk/neodc'
SERVE = 'https://dap.ceda.ac.uk/neodc'

# leicester, uol, and ocpr are different names for same thing
modlist  = ['besd', 'wfmd', 'imap', 'ocpr', 'leicester', 'uol']
varlist  = ['co2', 'ch4']
satlist  = ['sciam', 'gosat']
satday0  = [datetime(2002,10, 1), datetime(2009, 4, 1)]
# There are BESD XCO2 GOSAT retrievals somewhere that I can't find
# Would only use for NRT
namelist = ['besd_co2_sciam', 'wfmd_co2_sciam', 'wfmd_ch4_sciam',
    'imap_ch4_sciam', 'ocpr_ch4_gosat', 'leicester_ch4_gosat', 'uol_ch4_gosat']

def setup(**xlargs):
    from . import default
    from .translators.euroghg import translate

#   Make everything sit in euroghg directory
    xlargs['head'] = xlargs.get('head', './data/euroghg')

    xlargs = default.setup(**xlargs)

    return xlargs

def build(**xlargs):
#   Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

#   Lower variables for ease
    modlo = mod.lower()
    varlo = var.lower()
    satlo = sat.lower()
    verlo = ver.lower()

#   Greedy match all SCIAMACHY abbreviations
    if satlo[:3] == 'sci': satlo = 'sciam'

#   Determine timespan
    jdbeg = xlargs.get('jdbeg', datetime(1980, 1, 1))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

#   Set version (ver) and archive directory (ardir) based on retrieval
    if modlo == 'besd':
        if varlo != 'co2' or satlo != 'sciam':
            sys.stderr.write('*** WARNING *** BESD retrieval only ' +
                'available for SCIAMACHY CO2\n')
            return xlargs
        if ver == '*': ver = 'v02.01.02r'
        ardir = 'esacci/ghg/data/crdp_4/SCIAMACHY/CO2_SCI_BESD/' + ver[:-1]
        fhead = 'ESACCI-GHG-L2-CO2-SCIAMACHY-BESD-'

    elif modlo == 'wfmd':
        if varlo not in ['co2', 'ch4'] or satlo != 'sciam':
            sys.stderr.write('*** WARNING *** WFMD retrieval only ' +
                'available for SCIAMACHY CO2 and CH4\n')
            return xlargs
        if ver == '*': ver = 'v4.0r'
        ardir = ('esacci/ghg/data/crdp_4/SCIAMACHY/' + var.upper() +
            '_SCI_WFMD/' + ver[:-1])
        fhead = 'ESACCI-GHG-L2-' + var.upper() + '-SCIAMACHY-WFMD-'

    elif modlo == 'imap':
        if varlo != 'ch4' or satlo != 'sciam':
            sys.stderr.write('*** WARNING *** IMAP-DOAS retrieval only ' +
                ' available for SCIAMACHY CH4\n')
            return xlargs
        if ver == '*': ver = 'v7.2r'
        ardir = 'esacci/ghg/data/crdp_4/SCIAMACHY/CH4_SCI_IMAP/' + ver[:-1]
        fhead = 'ESACCI-GHG-L2-CH4-SCIAMACHY-IMAP-'

    elif modlo in ['leicester', 'uol', 'ocpr']:
        if varlo != 'ch4' or satlo != 'gosat':
            sys.stderr.write('*** WARNING *** Leicester retrieval only ' +
                'available for GOSAT CH4\n')
            return xlargs
        if ver == '*': ver = 'v9.0r'
        ardir = 'gosat/data/ch4/nceov1.0/CH4_GOS_OCPR'
        fhead = 'UoL-GHG-L2-CH4-GOSAT-OCPR-'

#   Set output directory
    if '*' in xlargs['daily']:
        xlargs['daily'] = (xlargs['head'] + '/' + mod + '/' + var +
            '/' + sat + '_' + ver + '_daily')

#   Set codas keys
    if xlargs.get('codas',False):
        xlargs['translate'] = lambda fin, ftr: translate(fin, ftr, var)
        xlargs['fhead'] = fhead
        if '*' in xlargs.get('fhout','*'):
            xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + ver + '.'
        if '*' in xlargs.get('chunk','*'):
            chops = xlargs['daily'].rsplit('_daily', 1)
            if len(chops) == 1: chops = chops + ['']
            xlargs['chunk'] = '_chunks'.join(chops)

#   Download
    wgargs = xlargs.get('wgargs', None)
    for nd in range(ndays):
        jdnow = jdbeg + timedelta(nd)
        yrnow = str(jdnow.year)
        yrget = str(jdnow.year)
        dget = yrget + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
        fget = '*-' + dget + '-*' + xlargs['ftail']

        pout = call(['wget', '--no-check-certificate'] + wgargs +
            [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y') + '/',
            '-A', fget, '-P', xlargs['daily'] + '/Y' + yrnow])

    return xlargs
