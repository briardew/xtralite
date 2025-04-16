'''
Initialize xtralite acquire module
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

# Define supported types
__all__ = ['acos', 'euroghg', 'nies', 'iasi', 'mopitt', 'tropess', 'tropomi']

# Load supported types and build dictionary
namedict = {}
for rr in __all__:
    exec('from . import %s' % rr)
    exec('namedict["%s"] = %s.namelist' % (rr,rr))
del(rr)
namelist = [value for key in namedict for value in namedict[key]]

# Utility to get appropriate module
def getmod(name):
    namelo = name.lower()
    for rr in __all__:
        for ss in namedict[rr]:
            sslo = ss.lower()
            if namelo.startswith(sslo) or sslo.startswith(namelo):
                return globals()[rr]
    return None
