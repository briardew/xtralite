#!/usr/bin/env python3
'''
Entry point for xtralite module
'''
# Copyright 2022-2023 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2022-04-26	Initial commit
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

def main():
    xlargs = vars(parser.parse_args())
    if xlargs['head'] is None: xlargs.pop('head')
    builder.build(**xlargs)

if __name__ == '__main__':
    sys.exit(main())
