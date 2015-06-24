#!/usr/bin/python -tt

import sys, os, multiprocessing, subprocess, tempfile

def usage():
        print sys.argv[0], 'SOURCE TARGET\n'
        print ' Scrape all image manifest files from SOURCE directory'
        print ' and copy them to TARGET. The files are then collated '
        print ' into a repository-wide repodata.json'
        sys.exit(1)

if len(sys.argv) != 3:
        usage()

###
#       1.        2.           3.
# 1. scrape.py  SOURCE      TMPCACHE
# 2. process.py TMPCACHE    REPODATADIR
# 3. cache.py   REPODATADIR 
###

source, repodatadir = sys.argv[1:3]
tmpcache = tempfile.mkdtemp()

scrape = subprocess.check_call(['./scrape.py', source, tmpcache])
process = subprocess.check_call(['./process.py', tmpcache, repodatadir])
cache = subprocess.check_call(['./cache.py', repodatadir])
