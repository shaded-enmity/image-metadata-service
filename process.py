#!/usr/bin/python -tt

import sys, os, multiprocessing, subprocess, json

data_root = '/tmp/manifests'
filter_string = '{arch: .architecture, digest: "sha256:%s", tag: .tag, name: .name, layers: [.fsLayers[].blobSum]}'\
                ' + (.history[0].v1Compatibility | fromjson | { os: .os, created: .created, labels: .config.Labels })'

def usage():
	print(os.path.basename(sys.argv[0]) + ' SOURCE TARGET\n')
        print(' Cache manifest metadata from SOURCE directory to TARGET')
        sys.exit(1)

def ensure_directory(name):
        if '/' in name:
                l, _ = name.split('/', 1)
                lroot = os.path.join(data_root, l)
                if not os.path.exists(lroot):
                        os.mkdir(lroot)
        target = os.path.join(data_root, name)
        if not os.path.exists(target):
                os.mkdir(target)

def filter_jq(target):
        bp = os.path.basename(target)
        r = subprocess.check_output(['jq', filter_string % bp, target])
        data = json.loads(r)
        subpath = data['name']
        del data['name']
        ensure_directory(subpath)
        fullpath = os.path.join(data_root, subpath, bp)
        with open(fullpath, 'w') as f:
                json.dump(data, f)
        return fullpath

def filter_manual(target):
        pass

if len(sys.argv) != 3:
        usage()

target, data_root, paths = sys.argv[1], sys.argv[2], []
for r, _, files in os.walk(target):
        for fl in files:
                paths.append(os.path.join(r, fl))

pool = multiprocessing.Pool(32)
manifest_map = filter(None, pool.map(filter_jq, paths))
if not manifest_map:
        sys.exit(1)
