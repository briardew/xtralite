'''
Convert retrievals into xtralite and chunk for assimilation with CoDAS
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

from glob import glob
from subprocess import call
import datetime as dtm
import numpy as np
import netCDF4, os
import xarray as xr

DEBUG   = False
VERBOSE = True
RMTMPS  = True

TNAMEDEF  = 'time'
RECDIMDEF = 'nsound'
FTAILDEF  = '.nc'

# Module only
__DIRIN   = ''
__DIROUT  = ''

#===============================================================================
def split3hr(fin, date, **xlargs):
    '''Split full-day netCDF file into 3-hour chunks'''
    LENHR = 10000

    TNAME  = xlargs.get('tname',  TNAMEDEF)
    RECDIM = xlargs.get('recdim', RECDIMDEF)
    FTAIL  = xlargs.get('ftail',  FTAILDEF)
    FHOUT  = xlargs['fhout']

    if VERBOSE: print('Splitting   ' + os.path.basename(fin))

#   1. Read time data
    ncfile = netCDF4.Dataset(fin, 'r') 
    itimes = ncfile.variables[TNAME][:]
    ncfile.close()

    nrec   = len(itimes)
    ihours = itimes//LENHR
    chunks = np.zeros([8, 4], dtype=int)

#   2. Compute indices to split at
    nF = -1
    for ic in range(8):
        it0 = 3*ic
        itF = 3*(ic + 1)

        n0 = nF + 1

#       assume failure
        chunks[ic,:] = [it0, itF, -1, -1]

        if nrec == n0: continue				# no records left to read?
        if itF <= ihours[n0]: continue			# no records in the interval?

#       success! add em up
        nF = n0
        while nF < nrec-1:
            if itF <= ihours[nF+1]: break
            nF = nF + 1

        chunks[ic,:] = [it0, itF, n0, nF]

    if DEBUG: print(chunks)

#   3. Write split files
    for ic in range(8):
        vals = chunks[ic,:]
        hour = str(vals[0]).zfill(2)
        ftmp = (xlargs['chunk'] + '/' + FHOUT + date + '_' + hour + 'z' +
            FTAIL + '.bit')
        if int(vals[2]) != -1:
            if VERBOSE: print('Writing ' + os.path.basename(ftmp))

            argc = RECDIM + ',' + str(vals[2]) + ',' + str(vals[3])
            if DEBUG: print(argc)
            pout = call(['ncks', '-h', '-O', '-d', argc, fin, ftmp])
            pout = call(['ncks', '-h', '-O', '--mk_rec_dmn',
                RECDIM, ftmp, ftmp])

    if RMTMPS: pout = call(['rm', fin])

#===============================================================================
# This subroutine should receive the two the file strings fleft, frite, and
# fout, which should be constructed in the chunker subroutine; that way we can
# test it easily; the for loop should thus go to chunker too
def paste6hr(date, dprv, **xlargs):
    '''Paste 3-hour files together into 6-hour chunks'''

    TNAME  = xlargs.get('tname',  TNAMEDEF)
    RECDIM = xlargs.get('recdim', RECDIMDEF)
    FTAIL  = xlargs.get('ftail',  FTAILDEF)
    FHOUT  = xlargs['fhout']

    if VERBOSE: print('---')
    for nh in [-3, 3, 9, 15]:
        jday  = dtm.datetime.strptime(date, '%Y%m%d')
        jleft = jday + dtm.timedelta(hours=nh)
        jrght = jday + dtm.timedelta(hours=nh+3)
        dleft = jleft.strftime('%Y%m%d_%H') + 'z'
        drght = jrght.strftime('%Y%m%d_%H') + 'z'

        fleft = xlargs['chunk'] + '/' + FHOUT + dleft + FTAIL + '.bit'
        frght = xlargs['chunk'] + '/' + FHOUT + drght + FTAIL + '.bit'
        fout  = __DIROUT        + '/' + FHOUT + drght + FTAIL

        flist = []
        if os.path.isfile(fleft): flist = flist + [fleft]
        if os.path.isfile(frght): flist = flist + [frght]

        if len(flist) > 0:
            if VERBOSE: print('Writing ' + os.path.basename(fout))

            xrout = xr.open_mfdataset(flist, mask_and_scale=False)
            xrout.attrs['input_files'] = ', '.join(flist)
            xrout.attrs['history'] = 'Created on ' + dtm.datetime.now().isoformat()
            contact = 'Brad Weir <briardew@gmail.com>'
            if 'contact' in xrout.attrs:
                contact = contact + ' / ' + xrout.attrs['contact']
            xrout.attrs['contact'] = contact
            xrout.to_netcdf(fout, encoding={RECDIM:{'dtype':'int32'}})
            xrout.close()

            if RMTMPS: pout = call(['rm', '-f', fleft, frght])

##   *** The logic of this could be much cleaner ***
##   a. Treat chunk that straddles two days differently
#    fleft = xlargs['chunk'] + '/' + FHOUT + dprv + '_21z' + FTAIL + '.bit'
#    frght = xlargs['chunk'] + '/' + FHOUT + date + '_00z' + FTAIL + '.bit'
#    fout  = __DIROUT + '/' + FHOUT + date + '_00z' + FTAIL
#
#    if os.path.isfile(fleft) and os.path.isfile(frght):
#        pout = call(['ncrcat', '-h', '-O', fleft, frght, fout])
##       Indicate combination of two days in input filenames
#        ncin  = netCDF4.Dataset(frght, 'r') 
#        ncout = netCDF4.Dataset(fout,  'a') 
#        ncout.input_files = ncout.input_files + ', ' + ncin.input_files
#        ncin.close()
#        ncout.close()
#    elif os.path.isfile(fleft):
#        pout = call(['cp', fleft, fout])
#    elif os.path.isfile(frght):
#        pout = call(['cp', frght, fout])
#
#    if VERBOSE: print('---')
#    if os.path.isfile(fleft) or os.path.isfile(frght):
#        if RMTMPS:  pout = call(['rm', '-f', fleft, frght])
#        if VERBOSE: print('Writing ' + os.path.basename(fout))
#
#        ncout = netCDF4.Dataset(fout, 'a')
#        ncout.history = 'Created on ' + dtm.datetime.now().isoformat()
#        contact = 'Brad Weir <briardew@gmail.com>'
#        if hasattr(ncout, 'contact'): contact = contact + ' / ' + ncout.contact
#        ncout.contact = contact
#
##   b. Rest of the chunks contained in single day
#    for nh in [3, 9, 15]:
#        fleft = (xlargs['chunk'] + '/' + FHOUT + date + '_' +
#                 str(nh  ).zfill(2) + 'z' + FTAIL + '.bit')
#        frght = (xlargs['chunk'] + '/' + FHOUT + date + '_' +
#                 str(nh+3).zfill(2) + 'z' + FTAIL + '.bit')
#        fout  = (__DIROUT        + '/' + FHOUT + date + '_' +
#                 str(nh+3).zfill(2) + 'z' + FTAIL)
#
#        if os.path.isfile(fleft) and os.path.isfile(frght):
#            pout = call(['ncrcat', '-h', '-O', fleft, frght, fout])
#        elif os.path.isfile(fleft):
#            pout = call(['cp', fleft, fout])
#        elif os.path.isfile(frght):
#            pout = call(['cp', frght, fout])
#
#        if os.path.isfile(fleft) or os.path.isfile(frght):
#            if RMTMPS:  pout = call(['rm', '-f', fleft, frght])
#            if VERBOSE: print('Writing ' + os.path.basename(fout))
#
#            ncout = netCDF4.Dataset(fout, 'a')
#            ncout.history = 'Created on ' + dtm.datetime.now().isoformat()
#            contact = 'Brad Weir <briardew@gmail.com>'
#            if hasattr(ncout, 'contact'): contact = contact + ' / ' + ncout.contact
#            ncout.contact = contact

#===============================================================================
def chunk(**xlargs):
    '''Run chunker over the specified days'''

    FHEAD = xlargs['fhead']
    FHOUT = xlargs['fhout']
    FTAIL = xlargs.get('ftail', FTAILDEF)
    trfun = xlargs['trfun']

    jdnow = xlargs['jdbeg']
    jdprv = jdnow + dtm.timedelta(-1)
    jdnxt = jdnow + dtm.timedelta(+1)

    if xlargs['yrdigs'] == 2:
        yrget = str(jdnow.year-2000).zfill(2)
    else:
        yrget = str(jdnow.year)

    dget = yrget           + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    dnow = str(jdnow.year) + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    dprv = str(jdprv.year) + str(jdprv.month).zfill(2) + str(jdprv.day).zfill(2)
    dnxt = str(jdnxt.year) + str(jdnxt.month).zfill(2) + str(jdnxt.day).zfill(2)

    global __DIRIN, __DIROUT
    __DIRIN  = xlargs['prep']  + '/Y' + str(jdnow.year)
    __DIROUT = xlargs['chunk'] + '/Y' + str(jdnow.year)

    flist = glob(__DIRIN  + '/' + FHEAD + dget + '*' + FTAIL)
    fouts = glob(__DIROUT + '/' + FHOUT + dnow + '*' + FTAIL)
    ftr   = xlargs['chunk'] + '/' + FHOUT + dnow + FTAIL + '.trans'

#   Only overwrite existing files if we are reprocessing
    if not xlargs.get('repro',False) and 0 < len(fouts): return

    if 0 < len(flist):
        if VERBOSE: print('---')

#       Use newest matching file for input (may be different versions)
        fin = sorted(flist, key=os.path.getmtime)[-1]

        print('Processing  ' + os.path.basename(fin))
        pout = call(['mkdir', '-p', __DIROUT])

#       Convert data to standard format
        if VERBOSE:
            print('Translating ' + os.path.basename(fin))
            print('         to ' + os.path.basename(ftr))
        trfun(fin, ftr)

#       Set input filename
        pout = call(['ncatted', '-h', '-O', '-a', 'input_files,global,o,c,' +
                     os.path.basename(fin), ftr])

#       Split day into 3-hour bits
        split3hr(ftr, dnow, **xlargs)

#   3. Paste 3-hour bits together into 6-hour chunks
#   (outside existence check to capture previous day's soundings)
    paste6hr(dnow, dprv, **xlargs)
