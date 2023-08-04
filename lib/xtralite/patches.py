'''
Monkey patches for xtralite
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2023/04/07	Initial commit
#
# Todo:
#===============================================================================

import xarray

# monkey path for xarray fill value bug (2023/04/07)
xarray.Dataset._to_netcdf_bug = xarray.Dataset.to_netcdf
def _to_netcdf_fix(self, *args, **kwargs):
    for name in self.variables:
        encoding = self.variables[name].encoding
        encoding['_FillValue'] = encoding.get('_FillValue', None)
        self.variables[name].encoding = encoding
    self._to_netcdf_bug(*args, **kwargs)
xarray.Dataset.to_netcdf = _to_netcdf_fix
