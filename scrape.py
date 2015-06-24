#!/usr/bin/python -tt

import sys, os, struct, shutil, multiprocessing

signature = (7020586390490450555,)
checker = struct.Struct("<Q")
checker_size = checker.size

def usage():
        print sys.argv[0], 'SOURCE TARGET\n'
        print ' Scrape all image manifest files from SOURCE directory'
        print ' and copy them to TARGET.'
        sys.exit(1)

def check_is_manifest(path):
        with open(path, 'r') as f:
                d = f.read(checker_size)
                if len(d) != checker_size:
                        return False
                return checker.unpack_from(d) == signature
        return False

def process_manifest(path, target):
        if check_is_manifest(path):
                ''' 
                /docker/registry/v2/blobs/<sha256>/<DD>/<FFFFFFFFFFFFFFFFFFFF>/data
                '''
                digest = path.split('/')[-2]
                shutil.copy(path, os.path.join(target, digest))
                return path

if len(sys.argv) != 3:
        usage()

directory = sys.argv[1]
target = sys.argv[2]
paths = []

for r, _, files in os.walk(directory):
        for fl in files:
                paths.append(os.path.join(r, fl))

def map_func(path):
        return process_manifest(path, target)

pool = multiprocessing.Pool(32)
manifest_map = filter(None, pool.map(map_func, paths))

print ' - source: {0} '.format(os.path.abspath(directory))
print ' - target: {0} '.format(os.path.abspath(target))
print ' - copied {0} manifests'.format(len(manifest_map))
