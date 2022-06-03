'''
Coarsen retrievals
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

import numpy as np

# Parameters for the below
NSTX = 1					# Stencil size along x (use odd)
NSTY = 1					# Stencil size along y (use odd)

def avg2d(var, NUMY, isok, mask):
    NUMX = var.size//NUMY
    NLOX = NUMX//NSTX
    NLOY = NUMY//NSTY

    var2d  =  var.reshape(NUMX, NUMY)
    isok2d = isok.reshape(NUMX, NUMY)

#   Numpy thinks NaN is a float, so need a little extra
    varavg = np.empty((NLOX, NLOY), dtype=var2d.dtype)
    varuse = np.zeros((NLOX, NLOY), dtype=bool)
    for mm in np.unique(mask):
#       Might chop off a few extra lines (we're coarsening anyways)
        varnum = np.zeros((NLOX, NLOY), dtype=int)
        vartot = np.zeros((NLOX, NLOY), dtype=var2d.dtype)

#       use2d = isok2d & (mm == mask.reshape(NUMX, NUMY))
        use2d = np.logical_and(isok2d, mm == mask.reshape(NUMX, NUMY))

#       NB: Iteration is over stencil size, typically very small
        for i0 in range(0,NSTX):
            for j0 in range(0,NSTY):
                varnum +=  use2d[i0:NLOX*NSTX:NSTX,j0:NLOY*NSTY:NSTY]
                vartot += (use2d[i0:NLOX*NSTX:NSTX,j0:NLOY*NSTY:NSTY] *
                           var2d[i0:NLOX*NSTX:NSTX,j0:NLOY*NSTY:NSTY])

        varavg[0 < varnum] = vartot[0 < varnum]/varnum[0 < varnum]
        varuse[0 < varnum] = True

    return varavg[varuse].reshape(varavg[varuse].size,)

#def find_medians(var, isok, mask):
#    NUMX = var.size//NUMY
#
##   Use (scanline, pixel) 2d arrays to do averaging
#    var2d  =  var.reshape(NUMX, NUMY)
#    isok2d = isok.reshape(NUMX, NUMY)
#
#    for mm in np.unique(mask):
#        NLOX = NUMX//NSTX
#        NLOY = NUMY//NSTY
#
##       Might chop off a few extra lines (we're coarsening anyways)
#        varnum = np.zeros((NLOX, NLOY), dtype=int)
#        vartot = np.zeros((NLOX, NLOY), dtype=var2d.dtype)
#
#        use2d = isok2d * (mm == mask.reshape(NUMX, NUMY))
#        var2d = var.reshape(NUMX, NUMY)
#        var2d[~use2d] = np.nan
#
##       Should switch this to median
##       With qc flag, not guaranteed odd number
#        for i0 in range(0,NSTX):
#            for j0 in range(0,NSTY):
#                nn = i0 + j0*NSTX
#                stack[:,:,nn] = var2d[i0:NLOX*NSTX:NSTX,j0:NLOY*NSTY:NSTY]
#
#        stack.sort along dimension 3
#        stack.pick middle value
#
#    return np.where(var == meds)[0]
