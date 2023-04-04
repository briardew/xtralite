#!/usr/bin/env python3
'''
Plot some stuff
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

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np
import datetime as dtm
import netCDF4

plt.rcParams['font.family'] = 'helvetica'

#--- TROPOMI CH4 ---
ff  = '../data/tropomi/ch4/s5p_v2.2f_daily/Y2022/tropomi_ch4_s5p_v2.2f.20220524.nc'
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['latitude'][:]
lon = ncf.variables['longitude'][:]
obs = ncf.variables['methane_mixing_ratio_bias_corrected'][:]
surfc = ncf.variables['surface_classification'][:]

ncf.close()

ax = plt.subplots(projection=ccrs.LambertCylindrical())
ax.coastlines()
ax.scatter(lon, lat, c=obs, s=1, marker='s', alpha=0.5,
    vmin=1750., vmax=2000., cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())
ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
plt.show()

#--- TROPOMI CO ---
ff  = '../data/tropomi/co/s5p_v2.2f_daily/Y2022/tropomi_co_s5p_v2.2f.20220524.nc'
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['latitude'][:]
lon = ncf.variables['longitude'][:]
obs = ncf.variables['carbonmonoxide_total_column'][:]
surfc = ncf.variables['surface_classification'][:]
sza = ncf.variables['solar_zenith_angle'][:]

iok = (surfc % 2 == 0) & (sza <= 60.)

ncf.close()

fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.Robinson()))
ax.scatter(lon[iok], lat[iok], c=obs[iok], s=1, marker='s', alpha=0.5,
    vmin=0.02, vmax=0.05, cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.coastlines()
plt.show()

#--- TROPOMI HCHO ---
ff  = '../data/tropomi/hcho/s5p_v2.2f_daily/Y2022/tropomi_hcho_s5p_v2.2f.20220524.nc'
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['latitude'][:]
lon = ncf.variables['longitude'][:]
obs = ncf.variables['formaldehyde_tropospheric_vertical_column'][:]
sza = ncf.variables['solar_zenith_angle'][:]
foot = ncf.variables['footprint'][:]

iok = (sza <= 60.) & (50 < foot) & (foot < 400)

ncf.close()

fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.Robinson()))
ax.scatter(lon[iok], lat[iok], c=obs[iok], s=1, marker='s', alpha=0.5,
    vmin=0., vmax=0.0002, cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.coastlines()
plt.show()

#--- TROPOMI SO2 ---
ff  = '../data/tropomi/so2/s5p_v2.2f_daily/Y2022/tropomi_so2_s5p_v2.2f.20220518.nc'
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['latitude'][:]
lon = ncf.variables['longitude'][:]
obs = ncf.variables['sulfurdioxide_total_vertical_column'][:]
sza = ncf.variables['solar_zenith_angle'][:]
foot = ncf.variables['footprint'][:]

iok = (sza <= 60.) & (50 < foot) & (foot < 400)

ncf.close()

fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.Robinson()))
ax.scatter(lon[iok], lat[iok], c=obs[iok], s=1, marker='s', alpha=0.5,
    vmin=0., vmax=0.001, cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.coastlines()
plt.show()

#--- TROPOMI NO2 ---
ff  = '../data/tropomi/no2/s5p_v2.2f_daily/Y2022/tropomi_no2_s5p_v2.2f.20220518.nc'
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['latitude'][:]
lon = ncf.variables['longitude'][:]
obs = ncf.variables['nitrogendioxide_summed_total_column'][:]

ncf.close()

fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.Robinson()))
ax.scatter(lon, lat, c=obs, s=1, marker='s', alpha=0.5,
    vmin=0., vmax=0.0001, cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.coastlines()
plt.show()

#--- TROPESS ---
var = 'nh3'
sat = 'cris-1'
vmin = 0.
vmax = 3.e-9

ff  = ('../data/tropess/' + var + '/' + sat + '_v1f_chunks/Y2022/tropess_' +
    var + '_' + sat +'_v1f.20220521_18z.nc')
ncf = netCDF4.Dataset(ff, 'r')

lat = ncf.variables['lat'][:]
lon = ncf.variables['lon'][:]
obs = ncf.variables['obs'][:]
# Seems unrealistic, maybe I missed some QC'ing
#unc = ncf.variables['uncert'][:]
#qcf = ncf.variables['isbad'][:]

ncf.close()

ax = plt.axes(projection=ccrs.LambertCylindrical())
ax.coastlines()
scat = ax.scatter(lon, lat, c=obs, s=1, marker='s', alpha=1.0,
    vmin=vmin, vmax=vmax, cmap='Purples', transform=ccrs.PlateCarree())
ax.set_extent([-180, 180, -90, 90], crs=ccrs.PlateCarree())
ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False)
plt.colorbar(scat, orientation='horizontal')
plt.show()

#--- European GHGs --
var = 'co2'
mod = 'wfmd'

if mod.lower() == 'besd': ver = 'v02.01.02'
if mod.lower() == 'wfmd': ver = 'v4.0'
if mod.lower() == 'imap': ver = 'v7.2'

lats  = None
lons  = None
obses = None
#ndays = 365
ndays = 30
jday0 = dtm.datetime(2003, 7, 1)

# Read
for nd in range(ndays):
    jday = jday0 + dtm.timedelta(nd)
    ff = ('../data/' + mod + '/' + var + '/sciamachy_' + ver + '_daily/Y' +
        jday.strftime('%Y') + '/ESACCI-GHG-L2-' + var + '-SCIAMACHY-' +
        mod.upper() + '-' + jday.strftime('%Y%m%d') + '-fv1.nc')
    try:
        ncf = netCDF4.Dataset(ff, 'r')
        lat = ncf.variables['latitude'][:]
        lon = ncf.variables['longitude'][:]
        obs = ncf.variables['x'+var.lower()][:]
        qcf = ncf.variables['x'+var.lower()+'_quality_flag'][:]
        iok = qcf == 0

        ncf.close()

        lats  = np.append(lats,  lat[iok])
        lons  = np.append(lons,  lon[iok])
        obses = np.append(obses, obs[iok])
    except Exception:
        pass

# Plot
fig, ax = plt.subplots(subplot_kw=dict(projection=ccrs.Robinson()))
ax.scatter(lons, lats, c=obses, s=1, marker='s', alpha=0.5,
    cmap='Spectral_r', transform=ccrs.PlateCarree())
ax.coastlines()
plt.show()
