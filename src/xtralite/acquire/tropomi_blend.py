#!/usr/bin/env python3

from os import path
from glob import glob
from netCDF4 import Dataset
import numpy as np
import pandas as pd
import pickle
import multiprocessing
import multiprocessing.pool
import sys
import gzip
import argparse

sys.dont_write_bytecode = True

# Correction factors from Balasus et al. (2023)
aa = 1.18
bb = -0.40


def predict_delta(file, model):
    # Transform TROPOMI netCDF file into pandas dataframe
    with Dataset(file) as ds:
        mask = ds['PRODUCT/qa_value'][:] == 1.0
        # Predictor variables (need to maintain compat w/ training)
        df = pd.DataFrame({
            "solar_zenith_angle": ds["PRODUCT/SUPPORT_DATA/GEOLOCATIONS/solar_zenith_angle"][:][mask],
            "relative_azimuth_angle": np.abs(180 - np.abs(ds["PRODUCT/SUPPORT_DATA/GEOLOCATIONS/solar_azimuth_angle"][:][mask] -
                ds["PRODUCT/SUPPORT_DATA/GEOLOCATIONS/viewing_azimuth_angle"][:][mask])),
            "across_track_pixel_index": np.expand_dims(np.tile(ds["PRODUCT/ground_pixel"][:], (mask.shape[1],1)), axis=0)[mask],
            "surface_classification": (ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/surface_classification"][:][mask] & 0x03).astype(int),
            "surface_altitude": ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/surface_altitude"][:][mask],
            "surface_altitude_precision": ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/surface_altitude_precision"][:][mask],
            "eastward_wind": ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/eastward_wind"][:][mask],
            "northward_wind": ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/northward_wind"][:][mask],
            "xch4_apriori": np.sum(ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/methane_profile_apriori"][:][mask]/
                np.expand_dims(np.sum(ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/dry_air_subcolumns"][:][mask], axis=1),axis=1), axis=1)*1e9,
            "reflectance_cirrus_VIIRS_SWIR": ds["PRODUCT/SUPPORT_DATA/INPUT_DATA/reflectance_cirrus_VIIRS_SWIR"][:][mask],
            "xch4_precision": ds["PRODUCT/methane_mixing_ratio_precision"][:][mask],
            "fluorescence": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/fluorescence"][:][mask],
            "co_column": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/carbonmonoxide_total_column"][:][mask],
            "co_column_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/carbonmonoxide_total_column_precision"][:][mask],
            "h2o_column": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/water_total_column"][:][mask],
            "h2o_column_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/water_total_column_precision"][:][mask],
            "aerosol_size": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_size"][:][mask],
            "aerosol_size_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_size_precision"][:][mask],
            "aerosol_height": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_mid_altitude"][:][mask],
            "aerosol_height_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_mid_altitude_precision"][:][mask],
            "aerosol_column": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_number_column"][:][mask],
            "aerosol_column_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_number_column_precision"][:][mask],
            "surface_albedo_SWIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/surface_albedo_SWIR"][:][mask],
            "surface_albedo_SWIR_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/surface_albedo_SWIR_precision"][:][mask],
            "surface_albedo_NIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/surface_albedo_NIR"][:][mask],
            "surface_albedo_NIR_precision": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/surface_albedo_NIR_precision"][:][mask],
            "aerosol_optical_thickness_SWIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_optical_thickness_SWIR"][:][mask],
            "aerosol_optical_thickness_NIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/aerosol_optical_thickness_NIR"][:][mask],
            "chi_square_SWIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/chi_square_SWIR"][:][mask],
            "chi_square_NIR": ds["PRODUCT/SUPPORT_DATA/DETAILED_RESULTS/chi_square_NIR"][:][mask]
        })

    df = df.add_prefix('tropomi_')

    return aa * model.predict(df) + bb


# Function to write a BLND file given a RPRO or OFFL file
def write_blended_files(file, model):
    print(f'Writing {file}', flush=True)

    with Dataset(file, 'a') as ds:
        product = ds.groups['PRODUCT']
        xch4a = product['methane_mixing_ratio_bias_corrected']
        mask = product['qa_value'][:] == 1.0

        # Add blended xch4
        vname = 'methane_mixing_ratio_blended'
        if vname not in product.variables:
            xch4b = product.createVariable(
                vname, xch4a.datatype, xch4a.dimensions
            )
            xch4b.setncatts(xch4a.__dict__)
            xch4b.setncattr(
                'comment', 'produced as described in Balasus et al. (2023)'
            )
        else:
            xch4b = product[vname]

        # model.predict fails with an empty dataframe
        if np.sum(mask) != 0:
            # Careful: netCDF4 doesn't like 2d masks and other ways to do this
            # produce garbage with no error messages
            xx = np.array(xch4a[:])
            xx[mask] = xx[mask] - predict_delta(file, model)
            xch4b[:] = xx

    return


def main():
    parser = argparse.ArgumentParser(
        description='TROPOMI-GOSAT blender',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        'dirin', metavar='dir', type=str, help='input directory'
    )
    parser.add_argument(
        'model', metavar='model', type=str, help='model pickle file'
    )
    args = parser.parse_args()

    if args.model.endswith('.gz'):
        with gzip.open(args.model, 'rb') as fid:
            model = pickle.load(fid)
    else:
        with open(args.model, 'rb') as fid:
            model = pickle.load(fid)

    # Write BLND files using as many cores as you have
    files = sorted(glob(path.join(args.dirin, '*.nc')))
    num_processes = min(multiprocessing.cpu_count(), len(files))
    with multiprocessing.Pool(processes=num_processes) as pool:
        pool.starmap(write_blended_files, [(ff, model) for ff in files])
        pool.close()
        pool.join()


if __name__ == '__main__':
    sys.exit(main())
