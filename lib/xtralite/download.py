'''
Downloading utility for xtralite
'''
# Copyright 2022 Brad Weir <briardew@gmail.com>. All rights reserved.
# Licensed under the Apache License 2.0, which can be obtained at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Changelog:
# 2023/05/04	Initial commit
#
# Todo:
#
# Notes:
#===============================================================================

WGETCMD = 'wget'
#WGETCMD = path.expanduser('~/bin/borg-wget.sh')

def download(strlist):
    pout = call(cmd + ' --load-cookies ~/.urs_cookies ' +
        '--save-cookies ~/.urs_cookies ' +
        '--auth-no-challenge=on --keep-session-cookies ' +
        '--content-disposition ' + ' '.join(wgargs) + ' ' +
        SERVE + '/' + ardir + '/' + 
        (jdnow + timedelta(mm)).strftime('%Y/%j') + '/' +
        ' -A "' + fwild + '" -P ' + DORBIT + '/Y' + yrnow, shell=True)

    if strlist[0] == 'wget':
        return call(strlist)
    elif strlist[0] == 'borg-wget':
