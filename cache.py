#!/usr/bin/python -tt

import sys, os, json, shutil, multiprocessing, datetime

target = sys.argv[1]
dirs = os.listdir(target)

for owner in dirs:
        fp = os.path.join(target, owner)
        for repo in os.listdir(fp):
                fe = os.path.join(fp, repo)
                collated = {'cached': str(datetime.datetime.utcnow()), 'images': []}
                for entry in os.listdir(fe):
                        path = os.path.join(fe, entry)
                        with open(path, 'r') as f:
                                collated['images'].append(json.load(f))
                cp = os.path.join(fe, 'repodata.json')
                with open(cp, 'w') as rdp:
                        json.dump(collated, rdp)
