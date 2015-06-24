#!/usr/bin/python -tt

import sys, os, json, datetime

def usage():
        print(sys.argv[0], 'TARGET\n')
        print(' Generate repodata.json from manifests stored at TARGET')
        sys.exit(1)

if len(sys.argv) != 2:
        usage()

target = sys.argv[1]
dirs = os.listdir(target)

for owner in dirs:
        fp = os.path.join(target, owner)
        for repo in os.listdir(fp):
                fe = os.path.join(fp, repo)
                collated = {'cached': str(datetime.datetime.utcnow()), 'repository': owner+'/'+repo, 'images': []}
                for entry in os.listdir(fe):
                        path = os.path.join(fe, entry)
                        with open(path, 'r') as f:
                                collated['images'].append(json.load(f))
                        os.remove(path)
                cp = os.path.join(fe, 'repodata.json')
                with open(cp, 'w') as rdp:
                        json.dump(collated, rdp)
