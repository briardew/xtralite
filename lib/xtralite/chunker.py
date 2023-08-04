'''
Convert retrievals into xtralite and chunk for assimilation with CoDAS
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
# * Improve filename handing to reduce/simplify calls to fhead, etc.
#===============================================================================

from glob import glob
from subprocess import call
from os import path
from datetime import datetime, timedelta

import numpy as np
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

DEBUG   = False
VERBOSE = True
RMTMPS  = True

TNAMEDEF  = 'time'
RECDIMDEF = 'nsound'
FTAILDEF  = '.nc'

#===============================================================================
def split3hr(fin, date, **xlargs):
    '''Split daily file into 3-hour chunks'''
    LENHR = 10000

    TNAME  = xlargs.get('tname',  TNAMEDEF)
    RECDIM = xlargs.get('recdim', RECDIMDEF)
    FTOUT  = xlargs.get('ftout',  FTAILDEF)
    FHOUT  = xlargs['fhout']

    if VERBOSE: print('Splitting   ' + path.basename(fin))

#   1. Read time data
    ds = xr.open_dataset(fin) 
    itimes = ds[TNAME].values
    ds.close()

    nrec = len(itimes)
    ihours = itimes//LENHR
    chunks = np.zeros([8, 4], dtype=int)

#   2. Compute indices to split at
    nF = -1
    for ic in range(8):
        n0 = nF + 1
        it0 = 3*ic
        itF = 3*(ic + 1)

#       Assume failure
        chunks[ic,:] = [it0, itF, -1, -1]

        if nrec == n0: continue				# no records left to read?
        if itF <= ihours[n0]: continue			# no records in the interval?

#       Success! add em up
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
        ftmp = path.join(xlargs['chunk'], FHOUT + date + '_' + hour + 'z' +
            '.bit' + FTOUT)

        if int(vals[2]) != -1:
            if VERBOSE: print('Writing ' + path.basename(ftmp))

            ds = xr.open_dataset(fin)
            ds = ds.isel({RECDIM:range(vals[2],vals[3]+1)})
            ds.to_netcdf(ftmp)
            ds.close()

    if RMTMPS: pout = call(['rm', fin])

#===============================================================================
# This subroutine should receive the two the file strings fleft, frite, and
# fout, which should be constructed in the chunker subroutine; that way we can
# test it easily; the for loop should thus go to chunker too
def paste6hr(date, dprv, **xlargs):
    '''Paste 3-hour files together into 6-hour chunks'''

    TNAME  = xlargs.get('tname',  TNAMEDEF)
    RECDIM = xlargs.get('recdim', RECDIMDEF)
    FTOUT  = xlargs.get('ftout',  FTAILDEF)
    FHOUT  = xlargs['fhout']

    jdnow = datetime.strptime(date, '%Y%m%d')

    DIROUT = path.join(xlargs['chunk'], 'Y' + str(jdnow.year))

    if VERBOSE: print('---')
    for nh in [-3, 3, 9, 15]:
        jleft = jdnow + timedelta(hours=nh)
        jrght = jdnow + timedelta(hours=nh+3)
        dleft = jleft.strftime('%Y%m%d_%H') + 'z'
        drght = jrght.strftime('%Y%m%d_%H') + 'z'

        fleft = path.join(xlargs['chunk'], FHOUT + dleft + '.bit' + FTOUT)
        frght = path.join(xlargs['chunk'], FHOUT + drght + '.bit' + FTOUT)
        fout  = path.join(DIROUT,          FHOUT + drght          + FTOUT)

        flist = []
        if path.isfile(fleft): flist = flist + [fleft]
        if path.isfile(frght): flist = flist + [frght]

        if len(flist) == 0: continue

#       Build input file list
        inlist = []
        for ff in flist:
            ds = xr.open_dataset(ff)
            for xx in ds.attrs['input_files'].split(', '):
                if xx not in inlist: inlist.append(xx)
            ds.close()
        input_files = ', '.join(inlist)

#       Only overwrite existing files if we are reprocessing
        if not path.isfile(fout) or xlargs.get('repro',False):
            if VERBOSE: print('Writing ' + path.basename(fout))

            pout = call(['mkdir', '-p', DIROUT])

            # An unfortunate hack to keep RECDIM dtype constant
            ds = xr.open_dataset(flist[0])
            dtype = ds[RECDIM].dtype
            ds.close()

            ds = xr.open_mfdataset(flist, mask_and_scale=False,
               combine='nested', concat_dim=RECDIM)
            ds = ds.assign_coords({RECDIM: ds[RECDIM].values.astype(dtype)})
            ds.attrs['input_files'] = input_files
            ds.attrs['history'] = 'Created on ' + datetime.now().isoformat()
            contact = 'Brad Weir <briardew@gmail.com>'
            if 'contact' in ds.attrs:
                contact = contact + ' / ' + ds.attrs['contact']
            ds.attrs['contact'] = contact
            ds.to_netcdf(fout)
            ds.close()

        if RMTMPS: pout = call(['rm', '-f', fleft, frght])

#===============================================================================
def chunk(**xlargs):
    '''Run chunker over the specified days'''

    FHEAD = xlargs['fhead']
    FTAIL = xlargs.get('ftail', FTAILDEF)
    FHOUT = xlargs['fhout']
    FTOUT = xlargs.get('ftout', FTAILDEF)
    translate = xlargs['translate']

    jdnow = xlargs['jdbeg']
    jdprv = jdnow + timedelta(-1)
    jdnxt = jdnow + timedelta(+1)

    if xlargs['yrdigs'] == 2:
        yrget = str(jdnow.year-2000).zfill(2)
    else:
        yrget = str(jdnow.year)

    dget = yrget           + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    dnow = str(jdnow.year) + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)
    dprv = str(jdprv.year) + str(jdprv.month).zfill(2) + str(jdprv.day).zfill(2)
    dnxt = str(jdnxt.year) + str(jdnxt.month).zfill(2) + str(jdnxt.day).zfill(2)

    DIRIN = path.join(xlargs['prep'], 'Y' + str(jdnow.year))

    flist = glob(path.join(DIRIN, FHEAD + dget + '*' + FTAIL))
    ftr = path.join(xlargs['chunk'], FHOUT + dnow + '.trans' + FTOUT)

    if 0 < len(flist):
        if VERBOSE: print('---')

#       Use newest matching file for input (may be different versions)
        fin = sorted(flist, key=path.getmtime)[-1]

        print('Processing  ' + path.basename(fin))
        pout = call(['mkdir', '-p', xlargs['chunk']])

#       Convert data to standard format
        if VERBOSE:
            print('Translating ' + path.basename(fin))
            print('         to ' + path.basename(ftr))
        translate(fin, ftr)

#       Set input filename
        with xr.open_dataset(ftr) as ds:
            ds.load()
        ds.attrs['input_files'] = path.basename(fin)
        ds.to_netcdf(ftr)
        ds.close()

#       Split day into 3-hour bits
        split3hr(ftr, dnow, **xlargs)

#   3. Paste 3-hour bits together into 6-hour chunks
#   (outside existence check to capture previous day's soundings)
    paste6hr(dnow, dprv, **xlargs)
