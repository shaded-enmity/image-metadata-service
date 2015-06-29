#!/usr/bin/python -tt

import argparse, datetime, functools, gnupg, json, multiprocessing, os, shlex, shutil, struct, subprocess, sys, tempfile

def scraper(obj, path):
        return obj.handle_file(path)

def mfilter(obj, manifest):
        return obj.filter_manifest(manifest)

class ManifestScraper(object):
        signature = (7020586390490450555,)
        checker = struct.Struct("<Q")
        checker_size = checker.size

        def __init__(self, src_dir, dst_dir):
                self.src_dir = src_dir
                self.dst_dir = dst_dir

        def is_manifest(self, path):
                with open(path, 'r') as f:
                        d = f.read(self.checker_size)
                        if len(d) != self.checker_size:
                                return False
                        return self.checker.unpack_from(d) == self.signature
                return False

        def handle_file(self, path):
                if self.is_manifest(path):
                        digest = path.split('/')[-2]
                        target = os.path.join(self.dst_dir, digest)
                        shutil.copy(path, target)
                        return target
                return None

        def process(self):
                paths = []
                for r, _, files in os.walk(self.src_dir):
                        for fl in files:
                                paths.append(os.path.join(r, fl))

                pool = multiprocessing.Pool(32)
                f = functools.partial(scraper, self)
                manifest_map = filter(None, pool.map(f, paths))

                return manifest_map

class ManifestFilter(object):
        filter_string = '{arch: .architecture, digest: "sha256:%s", tag: .tag, name: .name, layers: [.fsLayers[].blobSum]}'\
                ' + (.history[0].v1Compatibility | fromjson | { os: .os, created: .created, labels: .config.Labels })'

        def __init__(self, manifest_list, dst_dir):
                self.manifests = manifest_list
                self.dst_dir = dst_dir

        def ensure_directory(self, name):
                if '/' in name:
                        l, _ = name.split('/', 1)
                        lroot = os.path.join(self.dst_dir, l)
                        if not os.path.exists(lroot):
                                os.mkdir(lroot)
                target = os.path.join(self.dst_dir, name)
                if not os.path.exists(target):
                        os.mkdir(target)
        
        def filter_manifest(self, target):
                bp = os.path.basename(target)
                r = subprocess.check_output(['jq', self.filter_string % bp, target])
                data = json.loads(r)
                subpath = data['name']
                del data['name']
                self.ensure_directory(subpath)
                fullpath = os.path.join(self.dst_dir, subpath, bp)
                with open(fullpath, 'w') as f:
                        json.dump(data, f)
                return fullpath

        def process(self):
                pool = multiprocessing.Pool(32)
                f = functools.partial(mfilter, self)
                manifest_map = filter(None, pool.map(f, self.manifests))

                return manifest_map

class ArtefactCacher(object):
        def __init__(self, target_dir):
                self.target = target_dir

        def cache(self, path, data):
                cp = os.path.join(path, 'repodata.json')
                with open(cp, 'w+') as rdp:
                        json.dump(data, rdp)
                return cp

        def process(self):
                artefacts = []
                for owner in os.listdir(self.target):
                        fp = os.path.join(self.target, owner)

                        for repo in os.listdir(fp):
                                fe = os.path.join(fp, repo)

                                collated = {
                                        'cached': str(datetime.datetime.utcnow()), 
                                        'repository': owner+'/'+repo, 
                                        'images': []
                                }

                                for entry in os.listdir(fe):
                                        path = os.path.join(fe, entry)
                                        with open(path, 'r') as f:
                                                collated['images'].append(json.load(f))
                                        os.remove(path)

                                artefacts.append(
                                        self.cache(fe, collated)
                                )

                return artefacts

class GPGHelper(object):
        def __init__(self, gpg_config):
                self.gpg = gnupg.GPG(gnupghome=gpg_config['gpg_homedir'])
                self.passphrase = gpg_config['gpg_passphrase']
                self.fingerprint = gpg_config['gpg_fingeprint']

        @staticmethod
        def verify_config(gpg_config):
                h = GPGHelper(gpg_config)
                fp = h.find_fingerprint(h.fingerprint)
                if not fp:
                        return False

                testsig = h.gpg.sign(
                        'abc', 
                        passphrase=h.passphrase, 
                        keyid=h.fingerprint
                )
                return testsig != None

        def find_fingerprint(self, fp):
                for k in self.gpg.list_keys():
                        if k['fingerprint'] == fp:
                                return k
                return None

        def create_key(self, key_config):
                key_input = self.gpg.gen_key_input(**key_config)
                k = self.gpg.gen_key(key_input)
                if not k:
                        raise Exception('Unable to generate key')

                return k.fingerprint

        def ensure_fingerprint(self, fp=None):
                key = self.find_fingerprint(fp)
                if not key:
                        key = self.find_fingerprint(
                                self.create_default_key()
                        )
                        assert key
                        with open('key.fingerprint', 'w') as f:
                                f.write(key['fingerprint'])
                return key['fingerprint']


class CacheSigner(object):
        def __init__(self, caches, gpg_config):
                self.caches = caches
                self.helper = GPGHelper(gpg_config)
                self.gpg = self.helper.gpg
                 

        def sign_file(self, fl, fp):
                key = self.helper.find_fingerprint(fp)

                s = self.gpg.sign_file(
                        fl,
                        keyid=key['subkeys'][0][0],
                        passphrase=self.helper.passphrase,
                        detach=True
                )

                return s

        def sign_file_path(self, path, fp):
                signature = self.sign_file(
                        open(path),
                        fp,
                )

                sigpath = path + '.asc'
                with open(sigpath, 'w') as f:
                        f.write(str(signature))
                
                return signature

        def verify_file_path(self, path):
                v = self.gpg.verify_data(
                        path + '.asc',
                        open(path).read()
                )
                return v

        def process(self):
                assert self.helper.fingerprint

                for c in self.caches:
                        r = self.sign_file_path(
                                c,
                                self.helper.fingerprint
                        )
                        assert r

                        v = self.verify_file_path(c)
                        assert v

class App(object):
        def __init__(self, source, target, conf):
                self.source = source
                self.target = target
                self.gpg_config = conf
                self.tmp_dir = None

        def run(self):
                self.tmp_dir = tempfile.mkdtemp()

                scraper = ManifestScraper(
                        self.source,
                        self.tmp_dir
                )
                manifests = scraper.process()
                manifest_filter = ManifestFilter(
                        manifests,
                        self.target
                )
                artefacts = manifest_filter.process()
                cacher = ArtefactCacher(self.target)
                caches = cacher.process()
                signer = CacheSigner(
                        caches,
                        self.gpg_config
                )

                shutil.rmtree(self.tmp_dir)

                return signer.process()


def get_cli_configuration():
        ap = argparse.ArgumentParser()

        ap.add_argument('source')
        ap.add_argument('target')

        ap.add_argument('-g', '--gpg-config')

        args = ap.parse_args()

        with open(args.gpg_config, 'r') as cfg:
                args.gpg_config = json.load(cfg)

        if not GPGHelper.verify_config(args.gpg_config):
                print('Bogus GPG configuration!')
                print(' run config.py and try again')

        return (args.source, args.target, args.gpg_config)

cfg = get_cli_configuration()
app = App(*cfg)
app.run()
