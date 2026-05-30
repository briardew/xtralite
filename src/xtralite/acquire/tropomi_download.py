#!/usr/bin/env python

# Original code by Hannah Zafar, edits by Brad Weir

import requests
#import json
import pandas as pd
import xarray as xr
import sys
from os import path, makedirs
import argparse
import re
from datetime import datetime, timedelta
from netrc import netrc
from time import sleep

VARLIST = ['ch4', 'co', 'hcho', 'so2', 'no2', 'o3']
MODELIST = ['RPRO', 'OFFL', 'NRTI']
DEFVER = None
DEFOUT = '.'
MAXTRIES = 10

token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
search_url = 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products'

def get_date(ss) -> datetime:
    try:
        return datetime.strptime(ss, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f'Invalid date format: "{date}". Expected YYYY-MM-DD.')

def get_tokens(username: str, password: str) -> tuple[str, str]:
    auth_data = {'client_id':'cdse-public', 'username':username,
        'password':password, 'grant_type':'password'}

    try:
        response = requests.post(token_url, data=auth_data)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f'Keycloak token creation failed. ' +
            'Reponse from the server was: {response.json()}')
    print('Authentication token retrieved')

    return response.json()['access_token'], response.json()['refresh_token']

def refresh_access_token(refresh_token: str) -> str:
    auth_data = {'client_id':'cdse-public', 'refresh_token':refresh_token,
        'grant_type': 'refresh_token'}

    try:
        response = requests.post(token_url, data=auth_data)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f'Access token refresh failed. ' +
            'Reponse from the server was: {response.json()}')
    print('Authentication token refreshed')

    return response.json()['access_token']

def get_orbits(var: str, today: datetime, mode=None, ver=DEFVER):
    product = 'L2__' + var.upper() + '_'*(6 - len(var))
    tomrw = today + timedelta(days=1)

    # Define querying variables
    # A full list of options is available at
    # https://catalogue.dataspace.copernicus.eu/odata/v1/Attributes(SENTINEL-5P)
    # But where are the possible values?
    f1 = "Collection/Name eq 'SENTINEL-5P'"
    f2 = ("Attributes/OData.CSC.StringAttribute/any(att:att/Name" +
        f" eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product}')")
    f3 = f"ContentDate/End gt {today.isoformat(timespec='milliseconds')}Z"
    f4 = f"ContentDate/Start lt {tomrw.isoformat(timespec='milliseconds')}Z"
    params = {
        '$filter':f"{f1} and {f2} and {f3} and {f4}",
        '$top':1000,
        '$orderby':'ContentDate/Start asc',
    }

    response = requests.get(search_url, params=params)
    if response.status_code != 200:
        if response.json().get('detail') is not None:
            print(response.json().get('detail').get('message'))
        response.raise_for_status()

    df = pd.DataFrame.from_dict(response.json()['value'])

    # Import features into dataframe and extract information
    if df.empty:
        return [], []
    titles0 = df['Name'].values.tolist()
    ids0 = df['Id'].values.tolist()

    # Narrow results by mode and/or version
    if mode is not None:
        pattern1 = re.compile('_' + mode.upper() + '_')
    else:
        pattern1 = re.compile('')

    if ver is not None:
        # Could improve the version parsing, but it's non-trivial
        pattern2 = re.compile(product + '_[0-9]{8}T[0-9]{6}_' +
            '[0-9]{8}T[0-9]{6}_[0-9]{5}_[0-9]{2}_' + f'{int(ver):02}')
    else:
        pattern2 = re.compile('')

    # Probably a more elegant way to apply regexs, but whatevs
    titles = []
    urls = []
    for nn in range(len(titles0)):
        if (pattern1.search(titles0[nn]) is not None and
            pattern2.search(titles0[nn]) is not None):
            titles.append(titles0[nn])
            urls.append('https://download.dataspace.copernicus.eu/odata/v1/' +
                'Products(' + ids0[nn] + ')/$value')

    return titles, urls

def download(var: str, date: datetime, mode=None, ver=DEFVER, dirout=DEFOUT):
    # Obtain token
    xx = netrc()
    username, _, password = xx.authenticators('identity.dataspace.copernicus.eu')
    access_token, refresh_token = get_tokens(username, password)

    # Perform OpenSearch query
    titles, urls = get_orbits(var, date, mode, ver)

    # Use OData to download files
    ## Create a session and update headers
    session = requests.Session()
    headers = {'Authorization': f'Bearer {access_token}'}
    session.headers.update(headers)

    ## Create download directory
    makedirs(dirout, exist_ok=True)

    ## Loop over queries to extract
    for url, title in zip(urls, titles):
        # Get request
        for nn in range(MAXTRIES):
            try:
                response = session.get(url, stream=True)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                access_token = refresh_access_token(refresh_token)
                headers = {'Authorization': f'Bearer {access_token}'}
                session.headers.update(headers)

        # Path to save file
        ff = path.join(dirout, title)

        # Write to file
        # This can throw a connection reset by peer error
        # Need to wrap it somehow, maybe as above
        with open(ff, 'wb') as fid:
            fid.write(response.content)

    print(f'Downloaded {len(titles)} files to {dirout}')

    return


def main():
    parser = argparse.ArgumentParser(description='TROPOMI downloader',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('var', metavar='var', type=str, choices=VARLIST,
        help='gas name: ' + ', '.join(VARLIST))
    parser.add_argument('date', metavar='yyyy-mm-dd', type=get_date,
        help='date')
    parser.add_argument('-m', '--mode', metavar='MODE', type=str,
        choices=MODELIST, help='data mode: ' + ', '.join(MODELIST))
    parser.add_argument('-v', '--ver', type=float, default=DEFVER,
        help='data version')
    parser.add_argument('-o', '--output', metavar='DIR', default=DEFOUT,
        help='output directory')

    # Read args and translate to input vars for download
    args = vars(parser.parse_args())
    args['dirout'] = args.pop('output')

    download(**args)


if __name__ == '__main__':
    sys.exit(main())
