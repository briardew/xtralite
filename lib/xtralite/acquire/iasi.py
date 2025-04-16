'''
IASI support for xtralite
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
from os import path
from subprocess import call
from datetime import datetime, timedelta

SERVE = 'https://cds-espri.ipsl.fr'
# HNO3 and other NRT products available from Eumetcast
# CH4 from C3S?
# Also cf acsaf.org

modname = 'iasi'
varlist = ['co', 'ch4', 'co2', 'hcooh', 'nh3', 'so2', 'hno3']
satlist = ['metop-a', 'metop-b', 'metop-c']
satday0 = [datetime(2007,10, 1), datetime(2012, 9, 1), datetime(2018,11, 1)]
namelist = [modname + '_' + vv for vv in varlist]

FTAIL = '.nc'

def setup(jdnow, **xlargs):
    from xtralite.acquire import default
    from xtralite.translate.iasi import translate

    mod = modname
    xlargs['mod'] = mod
    xlargs['ftail'] = FTAIL

    xlargs = default.setup(jdnow, **xlargs)

    var = xlargs['var']
    sat = xlargs['sat']

    varup = var.upper()
    satup = sat.upper()
    yrnow = str(jdnow.year)
    dget  = yrnow + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)

    # Set version and filename based on variable and date
    if varup == 'CH4' or varup == 'CO2':
        if jdnow < datetime(2024, 7, 1):
            ver   = 'v10.2r'
            verin = 'V10.2'
        else:
            ver   = 'v10.1r'
            verin = 'V10.1'
        fhead = varup + '_IASI' + satup[-1] + '_NLIS_' + verin.lower() + '_'
        fget  = fhead + dget + FTAIL
    elif varup == 'HCOOH':
        ver   = 'v1.0r'
        verin = 'V1.0.0'
        fhead = 'IASI_METOP' + satup[-1] + '_L2_' + varup + '_COLUMN_'
        fget  = fhead + dget + '_ULB-LATMOS_' + verin + FTAIL
    elif varup == 'NH3':
        ver   = 'v3.1r'
        verin = 'V3.1.0'
        fhead = 'IASI_METOP' + satup[-1] + '_L2_' + varup + '_'
        fget  = fhead + dget + '_ULB-LATMOS_' + verin + FTAIL
    elif varup == 'SO2':
        ver   = 'v2.1r'
        verin = 'V2.1.0'
        fhead = 'IASI_METOP' + satup[-1] + '_L2_' + varup + '_'
        fget  = fhead + dget + '_ULB-LATMOS_' + verin + FTAIL
    # Someone always has to be special
    elif varup == 'CO':
        ver    = 'v1.2.1r'
        verin  = 'V1.2.1'
        verget = 'CDR_' + verin
        if satup[-1] == 'B':
            if datetime(2024, 1, 1) <= jdnow:
                ver    = 'v6.7.1f'
                verin  = 'V6.7.1'
                verget = 'ICDR_' + verin
        elif satup[-1] == 'C':
            if datetime(2023, 3,31) <= jdnow:
                ver    = 'v6.7.1f'
                verin  = 'V6.7.1'
                verget = 'ICDR_' + verin
            else:
                ver    = 'v6.5.1f'
                verin  = 'V6.5.1'
                verget = 'ICDR_' + verin

        fhead = 'IASI_METOP' + satup[-1] + '_L2_' + varup + '_'
        fget  = fhead + dget + '_ULB-LATMOS_' + verget + FTAIL

    # Directory and filename information
    head  = xlargs['head']
    daily = path.join(head, mod, var, sat + '_' + ver + '_daily')
    chunk = path.join(head, mod, var, sat + '_' + ver + '_chunks')

    xlargs['daily'] = daily
    xlargs['prep']  = daily
    xlargs['chunk'] = chunk

    xlargs['fhead'] = fhead
    xlargs['fget']  = fget
    xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + ver + '.'
    xlargs['ardir'] = ('iasi' + sat[-1].lower() + 'l2/' +
        'iasi_' + var.lower() + '/' + verin)
    xlargs['wgargs'] = ['-N', '-c']

    if '*' not in var: xlargs['translate'] = translate[var.lower()]

    return xlargs

def acquire(jdnow, **xlargs):
    # Get retrieval arguments
    xlargs = setup(jdnow, **xlargs)
    fget  = xlargs['fget']
    ardir = xlargs['ardir']
    wgargs = xlargs.get('wgargs', None)

    # Download
    yrnow = str(jdnow.year)

    # Download daily files
    cmd = (['wget', '--no-check-certificate'] + wgargs +
        [SERVE + '/' + ardir + '/' + jdnow.strftime('%Y/%m') +
        '/' + fget, '-P', xlargs['daily'] + '/Y' + yrnow])
    pout = call(cmd)

    return xlargs
