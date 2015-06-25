#!/usr/bin/python -tt

import sys, subprocess, tempfile, argparse, json, os

def usage():
	print(os.path.basename(sys.argv[0]) + ' SOURCE TARGET\n')
	print ' Scrape all image manifest files from SOURCE directory'
	print ' and copy them to TARGET. The files are then collated '
	print ' into a repository-wide repodata.json'
	sys.exit(1)

ap = argparse.ArgumentParser()
ap.add_argument('--confdir', '-c')
ap.add_argument('SOURCE')
ap.add_argument('TARGET')

config = None
confdir = 'conf/'
args = ap.parse_args()
if hasattr(args, 'confdir'):
	confdir = args.confdir
source = args.SOURCE
repodatadir = args.TARGET

cp = os.path.join(confdir, 'ims.json')
with open(cp, 'r') as f:
	config = json.load(f)

# Add parameters:
#
# gpg home dir (keyrings), fingerprint to sign with,
# path to default key config

if len(sys.argv) != 3:
        usage()

###
#       1.        2.           3.
# 1. scrape.py  SOURCE      TMPCACHE
# 2. process.py TMPCACHE    REPODATADIR
# 3. cache.py   REPODATADIR 
# 4. sign.py    REPODATADIR [FINGERPRINT]
###

tmpcache = tempfile.mkdtemp()

scrape = subprocess.check_call(['./scrape.py', source, tmpcache])
process = subprocess.check_call(['./process.py', tmpcache, repodatadir])
cache = subprocess.check_call(['./cache.py', repodatadir])
sign = subprocess.check_call(['./sign.py', repodatadir, 0])
