'''
xtralite: Acquire, build, and prepare constituent data for assimilation
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

__version__ = '0.0.1'
__author__ = 'Brad Weir'
__all__ = ['chunker', 'retrievals', 'build']

from xtralite import chunker
from xtralite import retrievals
from xtralite._build import build
