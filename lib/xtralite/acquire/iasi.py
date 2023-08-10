'''
IASI support for xtralite
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

SERVE = 'https://cds-espri.ipsl.fr'
# HNO3 and other NRT products available from Eumetcast
# CH4 from C3S
# Also cf acsaf.org

varlist = ['co', 'ch4', 'co2', 'hcooh', 'nh3', 'so2', 'hno3']
satlist = ['metop-a', 'metop-b', 'metop-c']
satday0 = [datetime(2007,10, 1), datetime(2012, 9, 1), datetime(2018,11, 1)]
namelist = ['iasi_' + vv for vv in varlist]

def setup(**xlargs):
    from xtralite.acquire import default
    from xtralite.translate.iasi import translate

    xlargs = default.setup(**xlargs)

    var = xlargs.get('var', '*')
    if '*' not in var:
        xlargs['translate'] = translate[var.lower()]

    return xlargs

def acquire(**xlargs):
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

    varlo = var.lower()
    satlet = sat[-1]

    # Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', datetime.now())
    ndays = (jdend - jdbeg).days + 1

    # Download
    wgargs = xlargs.get('wgargs', None)
    for nd in range(ndays):
        jdnow = jdbeg + timedelta(nd)
        yrnow = str(jdnow.year)
        dget = yrnow + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)

        # Set version and filename based on variable and date
        ftail = '.nc'
        if varlo == 'ch4' or varlo == 'co2':
            verin  = 'V9.1'
            verout = 'v9.1r'
            fhead  = (var.upper() + '_IASI' + satlet.upper() + '_NLIS_' +
                verin.lower() + '_')
            fget   = fhead + dget + ftail
        if varlo == 'hcooh':
            verin  = 'V1.0.0'
            verout = 'v1.0r'
            fhead  = ('IASI_METOP' + satlet.upper() + '_L2_' + var.upper() +
                '_COLUMN_')
            fget   = fhead + dget + '_ULB-LATMOS_' + verin + ftail
        if varlo == 'nh3':
            verin  = 'V3.1.0'
            verout = 'v3.1r'
            fhead  = ('IASI_METOP' + satlet.upper() + '_L2_' + var.upper() +
                '_')
            fget   = fhead + dget + '_ULB-LATMOS_' + verin + ftail
        if varlo == 'so2':
            verin  = 'V2.1.0'
            verout = 'v2.1r'
            fhead  = ('IASI_METOP' + satlet.upper() + '_L2_' + var.upper() +
                '_')
            fget   = fhead + dget + '_ULB-LATMOS_' + verin + ftail

        # Someone always has to be special
        if varlo == 'co':
            verin  = 'v20151001'
            verbug = 'V20151001.0'
            verout = 'v2015r'
            if datetime(2019, 5,14) <= jdnow:
                verin  = 'V6.4.0'
                verbug = verin
                verout = 'v6.4f'
            if datetime(2019,12, 5) <= jdnow:
                verin  = 'V6.5.0'
                verbug = verin
                verout = 'v6.5f'

            fhead = 'IASI_METOP' + satlet.upper() + '_L2_' + var.upper() + '_'
            fget  = fhead + dget + '_ULB-LATMOS_' + verbug + ftail

        # Set and check version
        veruse = verout if ver == '*' else ver

        if veruse.lower() != verout.lower():
            sys.stderr.write(("*** WARNING *** Specified version (%s) " +
                "doesn't match current version (%s)\n") % (veruse, verout))
            continue

        ardir = ('iasi' + satlet.lower() + 'l2/' +
            'iasi_' + var.lower() + '/' + verin)

        # Directory and filename information (may not be needed)
        if '*' in xlargs['daily']:
            xlargs['daily'] = path.join(xlargs['head'], mod, var,
                sat + '_' + veruse + '_daily')

        if '*' in xlargs.get('chunk','*'):
            chops = xlargs['daily'].rsplit('_daily', 1)
            if len(chops) == 1: chops = chops + ['']
            xlargs['chunk'] = '_chunks'.join(chops)

        xlargs['fhead'] = fhead
        xlargs['ftail'] = ftail
        xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + veruse + '.'

        # Download daily files
        cmd = (['wget', '--no-check-certificate'] + wgargs +
            [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y/%m') + '/' +
            fget, '-P', xlargs['daily'] + '/Y' + yrnow])
        pout = call(cmd)

    return xlargs
