'''
TROPOMI support for xtralite
'''
# Copyright 2022 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Todo:
# * Pressure/altitude grid
# * Only works with RMORBS on, I think because the overlapping _two files
#   don't get updated properly
#
# Notes:
# * CO is on a fixed altitude grid that's something like every 500 m
# * CH4 is on eta levels, but returns an altitude_levels variable
# * HCHO, SO2, and NO2 are on eta levels with the ak and bk values provided
#   albeit in a strange format
#===============================================================================

import datetime as dtm
import sys
from os.path import expanduser

modname  = 'tropomi'
varlist  = ['ch4', 'co', 'hcho', 'so2', 'no2', 'o3']
satlist  = ['s5p']
satday0  = [dtm.datetime(2018, 4, 1)]
namelist = [modname + '_' + vv for vv in varlist]

SERVE = 'https://tropomi.gesdisc.eosdis.nasa.gov/data'
WGETCMD = 'wget'
#WGETCMD = expanduser('~/bin/borg-wget.sh')

RMTMPS = True				# remove temporary files?
RMORBS = True				# remove orbit files?

RECDIM = 'sounding'			# shares name with nsound from chunk format
FTAIL  = '.nc'
TIME0  = dtm.datetime(2010, 1, 1)

def setup(**xlargs):
    from xtralite.retrievals import default
    from xtralite.retrievals.translate.tropomi import translate

    xlargs['ftail'] = xlargs.get('ftail', FTAIL)

    xlargs = default.setup(**xlargs)

    var = xlargs.get('var', '*')
    if '*' not in var: xlargs['trfun'] = translate[var]

    return xlargs

def build(**xlargs):
    from subprocess import call
    from os import remove, rmdir
    from os.path import isfile
    from glob import glob
    import numpy as np
    import xarray as xr
    import netCDF4

#   Get retrieval arguments
    mod = xlargs.get('mod', '*')
    var = xlargs.get('var', '*')
    sat = xlargs.get('sat', '*')
    ver = xlargs.get('ver', '*')

#   Variables that everything has
    dnames    = ['layer']
    vnamesaux = ['time', 'delta_time', 'ground_pixel']
    vnames0d  = []
    vnames1d  = ['latitude', 'longitude', 'solar_zenith_angle',
        'surface_pressure', 'qa_value', 'surface_classification',
        'processing_quality_flags']
    vnames2d  = []

#   Gas-dependent variables (move to a function/yaml?)
#   ---
#   Defaults
    LANDONLY = False			# Land only?
    QAMIN = 0.50			# Minimum qa_value to accept
    CLMAX = 0.10			# Maximum value of cloud variable
    VCLOUD = 'cloud_fraction_crb'	# Cloud variable
    VCHECK = ''				# Variable whose mask we use

    if var.lower() == 'ch4':
        LANDONLY = True
        CLMAX = float('nan')
        VCLOUD = ''
        VCHECK = 'methane_mixing_ratio_bias_corrected'
        dnames = dnames + ['level']
        vnames1d  = vnames1d  + ['methane_mixing_ratio',
            'methane_mixing_ratio_bias_corrected',
            'methane_mixing_ratio_precision']
        vnames2d  = vnames2d  + ['column_averaging_kernel',
            'methane_profile_apriori', 'altitude_levels', 'dry_air_subcolumns']

    if var.lower() == 'co':
        CLMAX = float('nan')
        VCLOUD = ''
        VCHECK = 'carbonmonoxide_total_column'
        vnames1d = vnames1d + ['surface_altitude',
            'carbonmonoxide_total_column',
            'carbonmonoxide_total_column_precision']
        vnames2d = vnames2d + ['column_averaging_kernel']

    if var.lower() == 'hcho':
        VCHECK = 'formaldehyde_tropospheric_vertical_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'formaldehyde_tropospheric_vertical_column',
            'formaldehyde_tropospheric_vertical_column_precision',
            'formaldehyde_tropospheric_vertical_column_trueness']
        vnames2d = vnames2d + ['averaging_kernel',
            'formaldehyde_profile_apriori']

    if var.lower() == 'so2':
        VCHECK = 'sulfurdioxide_total_vertical_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'sulfurdioxide_total_vertical_column',
            'sulfurdioxide_total_vertical_column_precision',
            'sulfurdioxide_total_vertical_column_trueness']
        vnames2d = vnames2d + ['averaging_kernel',
            'sulfurdioxide_profile_apriori']

    if var.lower() == 'no2':
        VCHECK = 'nitrogendioxide_summed_total_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'nitrogendioxide_slant_column_density',
            'nitrogendioxide_summed_total_column',
            'nitrogendioxide_summed_total_column_precision']
        vnames2d = vnames2d + ['averaging_kernel']

    if var.lower() == 'o3':
        VCHECK = 'ozone_total_vertical_column'
        dnames = dnames + ['level']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'ozone_total_vertical_column',
            'ozone_total_vertical_column_precision']
        vnames2d = vnames2d + ['averaging_kernel', 'ozone_profile_apriori',
            'pressure_grid']

    vnames = vnamesaux + vnames0d + vnames1d + vnames2d

#   Determine timespan
    jdbeg = xlargs.get('jdbeg', min(satday0))
    jdend = xlargs.get('jdend', dtm.datetime.now())
    ndays = (jdend - jdbeg).days + 1

    wgargs = xlargs.get('wgargs', None)
    for nd in range(ndays):
        jdnow = jdbeg + dtm.timedelta(nd)
        yrnow = str(jdnow.year)
        dnow = yrnow + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)

#       Determine version based on date
        vernow = 'v1.3f'
        if dtm.datetime(2019, 8, 6) < jdnow: vernow = 'v1.4f'
        if dtm.datetime(2021, 7, 1) < jdnow: vernow = 'v2.2f'

        veruse = ver
        if ver == '*': veruse = vernow

        if veruse.lower() != vernow.lower():
            sys.stderr.write(("*** WARNING *** Specified version (%s) " +
                "doesn't match current version (%s)\n") % (veruse, vernow))
            continue

#       Directory and filename information (needs some cleaning)
        if '*' in xlargs['daily']:
            xlargs['daily'] = (xlargs['head'] + '/' + mod + '/' + var +
                '/' + sat + '_' + veruse + '_daily')

        DLITE  = xlargs['daily']
        DIRTMP = DLITE + '/tmp'
        DORBIT = DLITE[:-6] + '_orbit'
        FHOUT  = 'tropomi_' + var + '_s5p_' + veruse + '.'

        if xlargs.get('codas',False) and '*' in xlargs.get('chunk','*'):
            chops = xlargs['daily'].rsplit('_daily', 1)
            if len(chops) == 1: chops = chops + ['']
            xlargs['chunk'] = '_chunks'.join(chops)
            xlargs['fhead'] = FHOUT
            xlargs['fhout'] = FHOUT

#       Continue if output exists and not reprocessing
        fout = DLITE + '/Y' + yrnow + '/' + FHOUT + dnow + FTAIL
        if isfile(fout) and not xlargs.get('repro',False):
            continue

#       Set archive directory (ardir)
        vardir = var.upper()
        if vardir == 'O3': vardir = vardir + '_TOT'
        ardir = (sat.upper() + '_TROPOMI_Level2/' + sat.upper() + '_L2__' +
            vardir + '_' * (6 - len(vardir)))
        if vernow == 'v1.3f': ardir = ardir +     '.1'
        if vernow == 'v1.4f': ardir = ardir + '_HiR.1'
        if vernow == 'v2.2f': ardir = ardir + '_HiR.2'

#       Download orbit files
        fwild = '*_' + dnow + 'T*_*' + FTAIL

        pout = call(['mkdir', '-p', DORBIT + '/Y' + yrnow])
        for mm in range(-1,2):
            pout = call(WGETCMD + ' --load-cookies ~/.urs_cookies ' +
                '--save-cookies ~/.urs_cookies ' +
                '--auth-no-challenge=on --keep-session-cookies ' +
                '--content-disposition ' + ' '.join(wgargs) + ' ' +
                SERVE + '/' + ardir + '/' + 
                (jdnow + dtm.timedelta(mm)).strftime('%Y/%j') + '/' +
                ' -A "' + fwild + '" -P ' + DORBIT + '/Y' + yrnow, shell=True)

#       Convert orbit files into daily lite files
#       ---
        flist  = glob(DORBIT + '/Y' + yrnow + '/' + fwild)
        sound0 = 0

#       Can do something like
#       0 = land, 1 = water; usually for CH4 you'll QC out a couple extra obs
#       Will need a way to recombine in order
#       pout = call(['ncap2', '-O', '-s', 'where(surface_classification % 2 == 0) VCHECK=VCHECK.get_miss();', fone, fone])
#       pout = call(['ncap2', '-O', '-s', 'where(surface_classification % 1 == 0) VCHECK=VCHECK.get_miss();', fone, fone])

        for ff in sorted(flist):
#           Create temporary filenames
            fone = ('_one' + FTAIL).join(ff.rsplit(FTAIL,1))
            ftwo = ('_two' + FTAIL).join(ff.rsplit(FTAIL,1))
            fone = fone.replace(DORBIT + '/Y' + yrnow, DIRTMP, 1)
            ftwo = ftwo.replace(DORBIT + '/Y' + yrnow, DIRTMP, 1)

            pout = call(['mkdir', '-p', DIRTMP])

#           Create temporary file with the variables we need (fone) and
#           empty file with just the dimensions we need (ftwo)
            pout = call(['ncks', '-O', '-3', '-G', ':', '-g', 'PRODUCT',
                '-v', ','.join(vnames), ff, fone])
            pout = call(['ncwa', '-O', '-a', 'time', fone, fone])
            pout = call(['ncks', '-O', '-3', '-v', ','.join(dnames), fone, ftwo])
            if len(vnames0d) > 0:
                pout = call(['ncks', '-A', '-v', ','.join(vnames0d), fone, ftwo])

#           Copy, reshape, and subset variables from fone to ftwo
            ncf1 = netCDF4.Dataset(fone, 'r') 
            ncf2 = netCDF4.Dataset(ftwo, 'a') 

#           Only copy obs with valid data in correct day (obuse)
#           About 2% of all soundings for CH4, almost everything for others
            obchk = ncf1.variables[VCHECK]
            time  = ncf1.variables['time']
            delt  = ncf1.variables['delta_time']
            vpix  = ncf1.variables['ground_pixel']
            qa    = ncf1.variables['qa_value']
            stype = ncf1.variables['surface_classification']

#           Recall time dimension was deleted above
            nscn = np.size(obchk, axis=0)
            npix = np.size(obchk, axis=1)

            if npix != vpix.size: raise

#           Some annoying logic to deal with different delta_time dimensions
#           HCHO and SO2 are unique with delta_time that has a ground_pixel
#           dimension and missing time_utc values
            dfix = delt[:].data[:,0] if (delt.shape == obchk.shape) else delt[:].data
            tscn = np.array([TIME0 + dtm.timedelta(seconds=int(time[:].data[()])) +
                dtm.timedelta(milliseconds=int(dd)) for dd in dfix])
            tsnd = np.repeat(tscn, npix)
            tuse = np.array([tt.date() == jdnow.date() for tt in tsnd])

#           Decide who to keep
            qause = ~np.less(qa, QAMIN)
            obuse = np.logical_and(~obchk[:].mask, qause).reshape(obchk.size,)
            obuse = np.logical_and(tuse, obuse)
            mask  = (stype[:] % 2).reshape(obchk.size,)

            if LANDONLY: obuse = np.logical_and(obuse, mask == 0)

#           Add cloud flags
            if 0 < len(VCLOUD):
                cloud = ncf1.variables[VCLOUD]
                cluse = np.less(cloud, CLMAX).reshape(obchk.size,)
                obuse = np.logical_and(obuse, cluse)

#           Create sounding dimension and variable
#           NB: Specifying fill_value causes xarray to muck up data type
            nsound = obuse[obuse].size
#           sdim = ncf2.createDimension(RECDIM, size=None)
            sdim = ncf2.createDimension(RECDIM, size=nsound)
            snum = ncf2.createVariable(RECDIM, 'int32', (RECDIM,))
            snum.units = '1'
            snum.long_name = 'S5P/TROPOMI sounding number'
            snum[:] = range(sound0, sound0 + nsound)
            sound0  = sound0 + nsound

#           Compute time for averaged sounding
            tdel = np.array([dd.total_seconds()
                for dd in (tsnd[obuse] - tsnd[0])])
            tavg = np.array([tsnd[0] + dtm.timedelta(seconds=ss)
                for ss in tdel])

#           Create ndate dimension and date variable
            tdim = ncf2.createDimension('ndate', size=7)
            date = ncf2.createVariable('date', 'int16', (RECDIM,'ndate'),
                fill_value=np.int16(-9999))
            date.units = 'none'
            date.long_name = 'Observation date and time matching sounding_id'
            date.comment = ('Year, month (1-12), day (1-31), hour (0-23), ' +
                'minute (0-59), second (0-59), millisecond (0-999). Note '  +
                'this time is chosen to correspond exactly to the digits '  +
                'in sounding_id')
            date[:] = np.array([(tt.year, tt.month, tt.day, tt.hour, tt.minute,
                tt.second, tt.microsecond//1000)
                for tt in tavg])

#           Create time variable
            time = ncf2.createVariable('time', 'float64', (RECDIM,),
                fill_value=np.float64(-9999.))
            time.units = 'seconds since ' + TIME0.strftime('%Y-%m-%d %H:%M:%S')
            time.long_name = 'time'
            time[:] = np.array([(tt - TIME0).seconds for tt in tavg])

#           Create footprint variable
            foot = ncf2.createVariable('footprint', vpix.dtype, (RECDIM,),
                fill_value=vpix._FillValue)
            foot.units = vpix.units
            foot.long_name = vpix.long_name
            foot.comment = vpix.comment
            foot[:] = np.tile(vpix, nscn)[obuse]

#           Read, reshape, and write 1D variables
            for vv in vnames1d:
                var1 = ncf1.variables[vv]
                var2 = ncf2.createVariable(vv, var1.dtype, (RECDIM,),
                    fill_value=var1._FillValue)
                var2.setncatts(var1.__dict__)
                var1rs  = var1[:].reshape(var1[:].size,)
                var2[:] = var1rs[:].data[obuse]

#           Read, reshape, and write 2D variables
            for vv in vnames2d:
                var1 = ncf1.variables[vv]
                var2 = ncf2.createVariable(vv, var1.dtype, (RECDIM,var1.dimensions[-1]),
                    fill_value=var1._FillValue)
                var2.setncatts(var1.__dict__)
                var1rs  = var1[:].reshape(var1[:,:,0].size, var1[0,0,:].size)
                for kk in range(np.size(var1rs,axis=1)):
                    var2[:,kk] = var1rs[obuse,kk]

#           Average sounding locations in spherical coordinates to account for
#           longitudinal periodicity
            latin = ncf1.variables['latitude']
            lonin = ncf1.variables['longitude']

#           Opposite cos/sin for lat than most formulas due to [-90,90] domain
            xx = np.cos(np.deg2rad(lonin[:].data)) * np.cos(np.deg2rad(latin[:].data))
            yy = np.sin(np.deg2rad(lonin[:].data)) * np.cos(np.deg2rad(latin[:].data))
            zz =                                     np.sin(np.deg2rad(latin[:].data))

            xxavg = xx.reshape(xx.size,)[obuse]
            yyavg = yy.reshape(yy.size,)[obuse]
            zzavg = zz.reshape(zz.size,)[obuse]
            rravg = np.sqrt(xxavg**2 + yyavg**2 + zzavg**2)

            latout = ncf2.variables['latitude']
            lonout = ncf2.variables['longitude']

            latout[:] = np.rad2deg(np.arcsin(zzavg/rravg))
            lonout[:] = np.rad2deg(np.arctan2(yyavg, xxavg))

#           Someone always has to be special
#           *** FIXME *** Double check date *** FIXME ***
            if var.lower() == 'co' and jdnow < dtm.datetime(2022, 2,23):
                avgker = ncf2.variables['column_averaging_kernel']
                avgker[:] = avgker[:]/1000.

            ncf1.close()
            ncf2.close()

#           Hack so ncrcat doesn't choke on files with no data
            if nsound == 0: pout = call(['rm', ftwo])

#       Create lite file from orbit files
        fcat = sorted(glob(DIRTMP + '/*_' + dnow + 'T*_*_two' + FTAIL))
        ftmp = fout.replace(DLITE + '/Y' + yrnow, DIRTMP, 1)
        if len(fcat) > 0:
            pout = call(['mkdir', '-p', DLITE + '/Y' + yrnow])

#           Concatenate, then convert back to netCDF4, two ways:
            dtmp = xr.open_mfdataset(fcat, mask_and_scale=False)
            dtmp.to_netcdf(ftmp, encoding={RECDIM:{'dtype':'int32'}})
            dtmp.close()

#           Create sounding_id variable once back in netCDF4
            ncf  = netCDF4.Dataset(ftmp, 'a')
            date = ncf.variables['date']
            foot = ncf.variables['footprint']

            sids = ncf.createVariable('sounding_id', 'uint64', (RECDIM,),
                fill_value=np.uint64(0))
            sids.units = 'HHMMSSFFFPPP'
            sids.long_name = 'S5P/TROPOMI sounding id'
            sids.comment = ('HH (hour), MM (minute), SS (second), FFF (millisecond), ' +
                'PPP (ground pixel)')
            duse = np.uint64(date[:].data)
            fuse = np.uint64(foot[:].data)
            sids[:] = (duse[:,3]*10**10 + duse[:,4]*10**8 +
                       duse[:,5]*10**6  + duse[:,6]*10**3 + fuse)

            if hasattr(ncf, 'history_of_appended_files'):
                delattr(ncf, 'history_of_appended_files')

            ncf.close()

#           Compress and overwrite history
            pout = call(['ncks', '-O', '-L', '9', ftmp, fout])
            pout = call(['ncatted', '-h', '-O', '-a', 'history,global,o,c,' +
                'Created on ' + dtm.datetime.now().isoformat(), fout])

#       Slightly terrifying
        if RMTMPS:
            for ff in glob(ftmp + '*'):
                remove(ff)
            for ff in glob(DIRTMP + '/*_' + dnow + 'T*_*' + FTAIL + '*'):
                remove(ff)
        if RMORBS:
            for ff in glob(DORBIT + '/Y' + yrnow + '/' + fwild + '*'):
                remove(ff)
            try:
                rmdir(DORBIT + '/Y' + yrnow)
            except Exception:
                pass
    if RMTMPS:
        try:
            rmdir(DIRTMP)
        except Exception:
            pass
    if RMORBS:
        try:
            rmdir(DORBIT)
        except Exception:
            pass

    return xlargs
