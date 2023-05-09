'''
Default support for xtralite
'''
# Copyright 2022 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
# * Add some warnings
#===============================================================================

from subprocess import call

def translate(fin, ftr):
    '''Translate input to CoDAS format'''
    pout = call(['cp', '-f', fin, ftr])

    return None

def setup(**xlargs):
    '''Define runtime arguments'''
#   Parse name into module, variable, satellite, version
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

#   Try to fill unspecified variables with existing values
    if len(mod) == 0: mod = xlargs.get('mod', '*')
    if len(var) == 0: var = xlargs.get('var', '*')
    if len(sat) == 0: sat = xlargs.get('sat', '*')
    if len(ver) == 0: ver = xlargs.get('ver', '*')

#   Fill arguments
    xlargs['mod'] = mod
    xlargs['var'] = var
    xlargs['sat'] = sat
    xlargs['ver'] = ver

#   Build directory names (can be templates for now)
    head  = xlargs.get('head',  './data')
    daily = xlargs.get('daily', '*')
    prep  = xlargs.get('prep',  '*')
    chunk = xlargs.get('chunk', '*')

    if '*' in daily:
        xlargs['daily'] = (head + '/' + mod + '/' + var + '/' +
            sat + '_' + ver + '_daily')

    if '*' in prep:
        xlargs['prep'] = xlargs['daily']

    if xlargs.get('codas',False) and '*' in chunk:
        chops = xlargs['daily'].rsplit('_daily', 1)
        if len(chops) == 1: chops = chops + ['']
        xlargs['chunk'] = '_chunks'.join(chops)

#   Build filename variables (can be templates for now)
    fhead = xlargs.get('fhead', '*')
    fhout = xlargs.get('fhout', '*')

    if '*' in fhead:
        xlargs['fhead']  = mod + '_' + var + '_' + sat + '_' + ver + '.'
    if '*' in fhout:
        xlargs['fhout']  = mod + '_' + var + '_' + sat + '_' + ver + '.'

    xlargs['ftail']  = xlargs.get('ftail',  '.nc')
    xlargs['yrdigs'] = xlargs.get('yrdigs', 4)
    xlargs['recdim'] = xlargs.get('recdim', 'nsound')
    xlargs['tname']  = xlargs.get('tname',  'time')
    xlargs['translate'] = xlargs.get('translate', translate)

#   Set wget arguments
    wgargs = ['-r', '-np', '-nd', '-e', 'robots=off']
    if not xlargs.get('repro',False):
#       wgargs = wgargs + ['-N']
        wgargs = wgargs + ['-nc']
    if xlargs.get('log',None) is not None:
        wgargs = wgargs + ['-nv', '-a', xlargs['log']]
    xlargs['wgargs']  = wgargs

    return xlargs
