'''
Default support for xtralite
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
# * Add some warnings
#===============================================================================

from os import path
from subprocess import check_call

def translate(fin, ftr):
    '''Translate input to CoDAS format'''
    pout = check_call(['cp', '-f', fin, ftr])

    return None

def setup(**xlargs):
    '''Define runtime arguments'''

    # Parse name as module_variable_satellite_version, e.g.,
    #     iasi_co_metop-a_v6.5f or iasi_co
    # Unspecified fields are set by module or arguments
    name = xlargs.get('name', '')
    ivar = name.find('_', 1)
    if ivar == -1: ivar = len(name)
    isat = name.find('_', ivar+1)
    if isat == -1: isat = len(name)
    iver = name.find('_', isat+1)
    if iver == -1: iver = len(name)
    mod = name[:ivar]
    var = name[ivar+1:isat]
    sat = name[isat+1:iver]
    ver = name[iver+1:]

    # Try to fill unspecified fields with existing values
    if len(mod) == 0: mod = xlargs.get('mod', '*')
    if len(var) == 0: var = xlargs.get('var', '*')
    if len(sat) == 0: sat = xlargs.get('sat', '*')
    if len(ver) == 0: ver = xlargs.get('ver', '*')

    # Fill arguments
    xlargs['mod'] = mod
    xlargs['var'] = var
    xlargs['sat'] = sat
    xlargs['ver'] = ver

    # Build directory names (can be templates for now)
    data = xlargs.get('head', 'data')
    daily = path.join(data, mod, var, sat + '_' + ver + '_daily')
    chunk = path.join(data, mod, var, sat + '_' + ver + '_chunks')
    if '*' in xlargs.get('daily', '*'): xlargs['daily'] = daily
    if '*' in xlargs.get('prep',  '*'): xlargs['prep']  = daily
    if '*' in xlargs.get('chunk', '*'): xlargs['chunk'] = chunk

    # Build filename variables (can be templates for now)
    fhead = mod + '_' + var + '_' + sat + '_' + ver + '.'
    if '*' in xlargs.get('fhead', '*'): xlargs['fhead'] = fhead
    if '*' in xlargs.get('fhout', '*'): xlargs['fhout'] = fhead

    xlargs['ftail']  = xlargs.get('ftail',  '.nc')
    xlargs['yrdigs'] = xlargs.get('yrdigs', 4)
    xlargs['recdim'] = xlargs.get('recdim', 'nsound')
    xlargs['tname']  = xlargs.get('tname',  'time')
    xlargs['translate'] = xlargs.get('translate', translate)

    # May want to expand this to a download command to support curl/sftp
    wgargs = ['-r', '-np', '-nd', '-e', 'robots=off']
    if not xlargs.get('repro',False):
        wgargs = wgargs + ['-nc']
    if xlargs.get('log',None) is not None:
        wgargs = wgargs + ['-nv', '-a', xlargs['log']]
    xlargs['wgargs'] = wgargs

    return xlargs
