#!/usr/bin/env python3
'''
Entry point for xtralite module
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022/04/26	Initial commit
#
# Todo:
#===============================================================================

import sys
from datetime import datetime
from argparse import ArgumentParser

from xtralite import acquire, builder

# Parse command-line options
class XLParser(ArgumentParser):
    def error(self, message):
        sys.stderr.write('\n*** ERROR **** %s\n\n' % message)
        self.print_help()
        sys.exit(2)

# Read arguments
parser = XLParser(description=__doc__,
    usage='xtralite name [options]',
    epilog='supported names: ' + ', '.join(acquire.namelist))
parser.add_argument('name', help='name of products to build ' +
    '(see list below)')
parser.add_argument('--beg', help='begin date (default: %(default)s)',
    default='1980-01-01')
parser.add_argument('--end', help='end date (default: %(default)s)',
    default=datetime.now().strftime('%Y-%m-%d'))
parser.add_argument('--codas', help='prepare for codas (default: false)',
    action='store_true')
parser.add_argument('--repro', help='reprocess/overwrite (default: false)',
    action='store_true')
parser.add_argument('--head', help='head data directory (default: data)')
parser.add_argument('--log', help='log file (default: stdout)')

#class Dataset:
#    var = ''
#    sat = ''
#    day0 = datetime(1979,12,31)

# * No consistency btwn euroghg and nies
# * Prefer not to have co2-swfp as a var name, e.g.
#   acos:
#       vars: co2
#       sats: gosat, oco2, oco3
#       tags: acos_gosat, acos_oco2, acos_oco3
#   euroghg:
#       mod: besd, wfmd, imap, ocpr, ocfp
#       var: co2, ch4
#       sat: sciam, gosat
#       euroghg/leic/co2/sciam_v9r_daily
#       euroghg/leic/ch4/gosat-swpr_v9r_daily
#       euroghg/leic/ch4/gosat-swfp_v9r_daily
#   nies:
#       mod: swfp, swpr, tir
#       var: co2, ch4
#       sat: gosat, gosat2
#       egs: nies_co2-tir_gosat2_v1.2f
#       nies/co2/tir/gosat2_v1.2f_daily
#       nies/co2/swfp/gosat2_v1.2f_daily
#       nies/ch4/swfp/gosat2_v1.2f_daily
#       nies/ch4/swpr/gosat2_v1.2f_daily
#   iasi:
#       vars: co, ch4, co2, hcooh, nh3, so2, hno3
#       sats: metop-a, metop-b, metop-c
#       egs: iasi_co_metop-a_v6.5f
#   mopitt:
#       mod: tir, nir
#       var: co
#       egs: mopitt_tir
#       mopitt/tir_v9r_daily/
#   tropess:
#       var: o3, co, ch4, nh3, pan, hdo
#       sat: airs, cris-s, cris-1
#       tropess/nh3/cris-s_v1f_daily
#   tropomi:
#       sat: ch4, co, hcho, so2, no2, o3

def main():
    xlargs = vars(parser.parse_args())
    if xlargs['head'] is None: xlargs.pop('head')
    builder.build(**xlargs)

if __name__ == '__main__':
    sys.exit(main())
