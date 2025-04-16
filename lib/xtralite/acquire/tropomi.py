'''
TROPOMI support for xtralite
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
#
# Todo:
# * Pressure/altitude grid
# * Only works with RMORBS on, I think because the overlapping _two files
#   don't get updated properly
# * Fix attributes
# * Move to native xarray (drop NCO and netCDF4 use)
#
# Notes:
# * CO is on a fixed altitude grid that's something like every 500 m
# * CH4 is on eta levels, but returns an altitude_levels variable
# * HCHO, SO2, and NO2 are on eta levels with the ak and bk values provided
#   albeit in a strange format
#===============================================================================

import sys
from os import path, remove, rmdir
from subprocess import call, PIPE, Popen
from glob import glob
from datetime import datetime, timedelta

import numpy as np
import netCDF4
# stop xarray from recasting coordinates
#import xarray as xr
from xtralite.patches import xarray as xr

VERDEF   = 'v2r'
modname  = 'tropomi'
varlist  = ['ch4', 'co', 'hcho', 'so2', 'no2', 'o3']
satlist  = ['s5p']
satday0  = [datetime(2018, 4,30)]
namelist = [modname + '_' + vv for vv in varlist]

# NB: This changes
JDNRT = datetime(2022, 7,26)

SERVE = 'https://tropomi.gesdisc.eosdis.nasa.gov/data'
WGETCMD = 'wget'
#WGETCMD = path.expanduser('~/bin/borg-wget.sh')

#wget "https://s5phub.copernicus.eu/dhus/search?q=beginPosition:[2023-07-05T00:00:00.000Z TO 2023-07-05T23:59:59.999Z] AND ( (platformname:Sentinel-5 AND producttype:L2__NO2___ AND processinglevel:L2 AND processingmode:Near real time))&rows=100&start=100" --output-document=query_results.txt
#for uuid in $(grep uuid query_results.txt | sed -e "s/.*>\(.*\)<.*/\1/"); do
#    wget --content-disposition --continue "https://s5phub.copernicus.eu/dhus/odata/v1/Products('$uuid')/\$value"
#done

RMTMPS = True				# remove temporary files?
RMORBS = True				# remove orbit files?

RECDIM = 'sounding'			# shares name with nsound from chunk format
FTAIL  = '.nc'
TIME0  = datetime(2010, 1, 1)

def setup(jdnow, **xlargs):
    from xtralite.acquire import default
    from xtralite.translate.tropomi import translate

    mod = modname
    xlargs['mod'] = mod
    xlargs['ftail'] = FTAIL

    xlargs = default.setup(jdnow, **xlargs)

    # Fill unspecified version with default and
    # flip to forward stream based on date
    ver = xlargs['ver']
    if ver == '*': ver = VERDEF
    if ver == VERDEF and JDNRT <= jdnow: ver = VERDEF[:-1] + 'f'
    xlargs['ver'] = ver

    # Fill directory and filename templates (needs improvement)
    sat   = xlargs['sat']
    var   = xlargs['var']
    head  = xlargs['head']

    daily = path.join(head, mod, var, sat + '_' + ver + '_daily')
    chunk = path.join(head, mod, var, sat + '_' + ver + '_chunks')

    xlargs['daily'] = daily
    xlargs['prep']  = daily
    xlargs['chunk'] = chunk

    xlargs['fhout'] = mod + '_' + var + '_' + sat + '_' + ver + '.'
    xlargs['fhead'] = mod + '_' + var + '_' + sat + '_' + ver + '.'
    if '*' not in var: xlargs['translate'] = translate[var.lower()]

    return xlargs

def acquire(jdnow, **xlargs):
    # Check for NCO utilities
    # (will be removed soon, some retrievals still use these)
    try:
        pout = Popen('ncks', stdout=PIPE)
    except OSError:
        sys.stderr.write('*** ERROR *** NCO executables not in $PATH\n\n')
        sys.exit(2)

    # Get retrieval arguments
    xlargs = setup(jdnow, **xlargs)
    mod = xlargs['mod']
    var = xlargs['var']
    sat = xlargs['sat']
    ver = xlargs['ver']
    wgargs = xlargs.get('wgargs', None)

    # Variables that everything has
    dnames    = ['layer']
    vnamesaux = ['time', 'delta_time', 'ground_pixel']
    vnames0d  = []
    vnames1d  = ['latitude', 'longitude', 'solar_zenith_angle',
        'viewing_zenith_angle', 'surface_pressure', 'qa_value',
        'surface_classification', 'processing_quality_flags']
    vnames2d  = []

    # Gas-dependent variables (move to a function/yaml?)
    # ---
    # Defaults
    LANDONLY = False			# Land only?
    QAMIN = 0.50			# Minimum qa_value to accept
    CLMAX = 0.10			# Maximum value of cloud variable
    VCLOUD = 'cloud_fraction_crb'	# Cloud variable
    VCHECK = ''				# Variable whose mask we use

    varlo = var.lower()
    if varlo == 'ch4':
        CLMAX = float('nan')
        VCLOUD = ''
        VCHECK = 'methane_mixing_ratio_bias_corrected'
        dnames = dnames + ['level']
        vnames1d  = vnames1d  + ['methane_mixing_ratio',
            'methane_mixing_ratio_bias_corrected',
            'methane_mixing_ratio_precision']
        vnames2d  = vnames2d  + ['column_averaging_kernel',
            'methane_profile_apriori', 'altitude_levels', 'dry_air_subcolumns']
    elif varlo == 'co':
        CLMAX = float('nan')
        VCLOUD = ''
        VCHECK = 'carbonmonoxide_total_column'
        vnames1d = vnames1d + ['surface_altitude',
            'carbonmonoxide_total_column',
            'carbonmonoxide_total_column_precision']
        vnames2d = vnames2d + ['column_averaging_kernel']
    elif varlo == 'hcho':
        VCHECK = 'formaldehyde_tropospheric_vertical_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'formaldehyde_tropospheric_vertical_column',
            'formaldehyde_tropospheric_vertical_column_precision',
            'formaldehyde_tropospheric_vertical_column_trueness']
        vnames2d = vnames2d + ['averaging_kernel',
            'formaldehyde_profile_apriori']
    elif varlo == 'so2':
        VCHECK = 'sulfurdioxide_total_vertical_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'sulfurdioxide_total_vertical_column',
            'sulfurdioxide_total_vertical_column_precision',
            'sulfurdioxide_total_vertical_column_trueness']
        vnames2d = vnames2d + ['averaging_kernel',
            'sulfurdioxide_profile_apriori']
    elif varlo == 'no2':
        VCHECK = 'nitrogendioxide_summed_total_column'
        vnames0d = vnames0d + ['tm5_constant_a', 'tm5_constant_b']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'nitrogendioxide_slant_column_density',
            'nitrogendioxide_summed_total_column',
            'nitrogendioxide_summed_total_column_precision']
        vnames2d = vnames2d + ['averaging_kernel']
    elif varlo == 'o3':
        VCHECK = 'ozone_total_vertical_column'
        dnames = dnames + ['level']
        vnames1d = vnames1d + ['cloud_fraction_crb',
            'ozone_total_vertical_column',
            'ozone_total_vertical_column_precision']
        vnames2d = vnames2d + ['averaging_kernel', 'ozone_profile_apriori',
            'pressure_grid']

    vnames = vnamesaux + vnames0d + vnames1d + vnames2d

    yrnow = str(jdnow.year)
    dnow  = yrnow + str(jdnow.month).zfill(2) + str(jdnow.day).zfill(2)

    DLITE  = xlargs['daily']
    DIRTMP = DLITE + '/tmp'
    DORBIT = DLITE[:-6] + '_orbit'
    FHOUT  = xlargs['fhout']

    # Return if output exists and not reprocessing
    fout = DLITE + '/Y' + yrnow + '/' + FHOUT + dnow + FTAIL
    if path.isfile(fout) and not xlargs.get('repro',False):
        return xlargs

    # Set archive directory (ardir)
    vardir = var.upper()
    if vardir == 'O3': vardir = vardir + '_TOT'
    ardir = (sat.upper() + '_TROPOMI_Level2/' + sat.upper() + '_L2__' +
        vardir + '_' * (6 - len(vardir)))
    if ver[:3] == 'v1L':
        ardir = ardir + '.1'
    elif ver[:3] == 'v1H':
        ardir = ardir + '_HiR.1'
    elif ver[:2] == 'v2':
        ardir = ardir + '_HiR.2'

    # Set wildcard for files to download
    if ver[-1] == 'r':
        fwild = '*_' + 'RPRO' + '_*_' + dnow + 'T*_*' + FTAIL
    elif ver[-1] == 'f':
        fwild = '*_' + 'OFFL' + '_*_' + dnow + 'T*_*' + FTAIL
    else:
        fwild = '*_' + '*'    + '_*_' + dnow + 'T*_*' + FTAIL

    # Download orbit files
    pout = call(['mkdir', '-p', DORBIT + '/Y' + yrnow])
    for mm in range(-1,2):
        pout = call(WGETCMD + ' --load-cookies ~/.urs_cookies ' +
            '--save-cookies ~/.urs_cookies ' +
            '--auth-no-challenge=on --keep-session-cookies ' +
            '--content-disposition ' + ' '.join(wgargs) + ' ' +
            SERVE + '/' + ardir + '/' + 
            (jdnow + timedelta(mm)).strftime('%Y/%j') + '/' +
            ' -A "' + fwild + '" -P ' + DORBIT + '/Y' + yrnow, shell=True)

    # Convert orbit files into daily lite files
    # ---
    sound0 = 0
    flist  = glob(DORBIT + '/Y' + yrnow + '/' + fwild)
    for ff in sorted(flist):
        # Create temporary filenames
        fone = ('_one' + FTAIL).join(ff.rsplit(FTAIL,1))
        ftwo = ('_two' + FTAIL).join(ff.rsplit(FTAIL,1))
        fone = fone.replace(DORBIT + '/Y' + yrnow, DIRTMP, 1)
        ftwo = ftwo.replace(DORBIT + '/Y' + yrnow, DIRTMP, 1)

        pout = call(['mkdir', '-p', DIRTMP])

        # Create temporary file with the variables we need (fone) and
        # empty file with just the dimensions we need (ftwo)
        pout = call(['ncks', '-O', '-3', '-G', ':', '-g', 'PRODUCT',
            '-v', ','.join(vnames), ff, fone])
        pout = call(['ncwa', '-O', '--no_cll_mth', '-a', 'time', fone, fone])
        pout = call(['ncks', '-O', '-3', '-v', ','.join(dnames), fone, ftwo])
        if len(vnames0d) > 0:
            pout = call(['ncks', '-A', '-v', ','.join(vnames0d), fone, ftwo])

        # Copy, reshape, and subset variables from fone to ftwo
        ncf1 = netCDF4.Dataset(fone, 'r') 
        ncf2 = netCDF4.Dataset(ftwo, 'a') 

        # Only copy obs with valid data in correct day (obuse)
        # About 2% of all soundings for CH4, almost everything for others
        obchk = ncf1.variables[VCHECK]
        time  = ncf1.variables['time']
        delt  = ncf1.variables['delta_time']
        vpix  = ncf1.variables['ground_pixel']
        qa    = ncf1.variables['qa_value']
        stype = ncf1.variables['surface_classification']

        # Recall time dimension was deleted above
        nscn = np.size(obchk, axis=0)
        npix = np.size(obchk, axis=1)

        if npix != vpix.size: raise

        # Some annoying logic to deal with different delta_time dimensions
        # HCHO and SO2 are unique with delta_time that has a ground_pixel
        # dimension and missing time_utc values
        dfix = delt[:].data[:,0] if (delt.shape == obchk.shape) else delt[:].data
        tscn = np.array([TIME0 + timedelta(seconds=int(time[:].data[()])) +
            timedelta(milliseconds=int(dd)) for dd in dfix])
        tsnd = np.repeat(tscn, npix)
        tuse = np.array([tt.date() == jdnow.date() for tt in tsnd])

        # Decide who to keep
        qause = ~np.less(qa, QAMIN)
        obuse = np.logical_and(~obchk[:].mask, qause).reshape(obchk.size,)
        obuse = np.logical_and(tuse, obuse)
        mask  = (stype[:] % 2).reshape(obchk.size,)

        if LANDONLY: obuse = np.logical_and(obuse, mask == 0)

        # Add cloud flags
        if 0 < len(VCLOUD):
            cloud = ncf1.variables[VCLOUD]
            cluse = np.less(cloud, CLMAX).reshape(obchk.size,)
            obuse = np.logical_and(obuse, cluse)

        # Create sounding dimension and variable
        # NB: Specifying fill_value causes xarray to muck up data type
        nsound = obuse[obuse].size

#       sdim = ncf2.createDimension(RECDIM, size=None)
        sdim = ncf2.createDimension(RECDIM, size=nsound)
        snum = ncf2.createVariable(RECDIM, 'int32', (RECDIM,))
        snum.units = '1'
        snum.long_name = 'S5P/TROPOMI sounding number'
        snum[:] = range(sound0, sound0 + nsound)
        sound0  = sound0 + nsound

        # Compute time for averaged sounding
        tdel = np.array([dd.total_seconds()
            for dd in (tsnd[obuse] - tsnd[0])])
        tavg = np.array([tsnd[0] + timedelta(seconds=ss)
            for ss in tdel])

        # Create ndate dimension and date variable
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

        # Create time variable
        time = ncf2.createVariable('time', 'float64', (RECDIM,),
            fill_value=np.float64(-9999.))
        time.units = 'seconds since ' + TIME0.strftime('%Y-%m-%d %H:%M:%S')
        time.long_name = 'time'
        time[:] = np.array([(tt - TIME0).seconds for tt in tavg])

        # Create footprint variable
        foot = ncf2.createVariable('footprint', vpix.dtype, (RECDIM,),
            fill_value=vpix._FillValue)
        foot.units = vpix.units
        foot.long_name = vpix.long_name
        foot.comment = vpix.comment
        foot[:] = np.tile(vpix, nscn)[obuse]

        # Read, reshape, and write 1D variables
        for vv in vnames1d:
            var1 = ncf1.variables[vv]
            var2 = ncf2.createVariable(vv, var1.dtype, (RECDIM,),
                fill_value=var1._FillValue)
            var2.setncatts(var1.__dict__)
            var1rs  = var1[:].reshape(var1[:].size,)
            var2[:] = var1rs[:].data[obuse]

        # Read, reshape, and write 2D variables
        for vv in vnames2d:
            var1 = ncf1.variables[vv]
            var2 = ncf2.createVariable(vv, var1.dtype, (RECDIM,var1.dimensions[-1]),
                fill_value=var1._FillValue)
            var2.setncatts(var1.__dict__)
            var1rs  = var1[:].reshape(var1[:,:,0].size, var1[0,0,:].size)
            for kk in range(np.size(var1rs,axis=1)):
                var2[:,kk] = var1rs[obuse,kk]

        # Average sounding locations in spherical coordinates to account for
        # longitudinal periodicity
        latin = ncf1.variables['latitude']
        lonin = ncf1.variables['longitude']

        # Opposite cos/sin for lat than most formulas due to [-90,90] domain
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

        # Someone always has to be special
        # *** Always good to double check ***
        if var.lower() == 'co' and ver[:2] == 'v1':
            avgker = ncf2.variables['column_averaging_kernel']
            avgker[:] = avgker[:]/1000.

        ncf1.close()
        ncf2.close()

        # Hack so ncrcat doesn't choke on files with no data
        if nsound == 0: pout = call(['rm', ftwo])

    # Create lite file from orbit files
    fcat = sorted(glob(DIRTMP + '/*_' + dnow + 'T*_*_two' + FTAIL))
    ftmp = fout.replace(DLITE + '/Y' + yrnow, DIRTMP, 1)
    if len(fcat) > 0:
        pout = call(['mkdir', '-p', DLITE + '/Y' + yrnow])

        # Concatenate, then convert back to netCDF4, two ways:
        dtmp = xr.open_mfdataset(fcat, mask_and_scale=False)
        dtmp.to_netcdf(ftmp, encoding={RECDIM:{'dtype':'int32'}})
        dtmp.close()

        # Create sounding_id variable once back in netCDF4
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

        # Compress and overwrite history
        pout = call(['ncks', '-O', '-L', '9', ftmp, fout])
        pout = call(['ncatted', '-h', '-O', '-a', 'history,global,o,c,' +
            'Created on ' + datetime.now().isoformat(), fout])

    # Slightly terrifying
    if RMTMPS:
        for ff in glob(ftmp + '*'):
            remove(ff)
        for ff in glob(DIRTMP + '/*_' + dnow + 'T*_*' + FTAIL + '*'):
            remove(ff)
        try:
            rmdir(DIRTMP)
        except Exception:
            pass
    if RMORBS:
        for ff in glob(DORBIT + '/Y' + yrnow + '/' + fwild + '*'):
            remove(ff)
        try:
            rmdir(DORBIT + '/Y' + yrnow)
        except Exception:
            pass
        try:
            rmdir(DORBIT)
        except Exception:
            pass

    return xlargs
