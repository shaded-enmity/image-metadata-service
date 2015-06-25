#!/usr/bin/python -tt

import sys, gnupg, os

if len(sys.argv) == 1:
	print(os.path.basename(sys.argv[0]) + ' TARGET [FINGERPRINT]\n')
	print(' Iterate over all repodata.json files in TARGET tree\n'\
	      ' and sign them using FINGERPRINT. If the FINGERPRINT\n'\
	      ' is not found, new key will be generated from default\n'\
	      ' config and stored in `$PWD/key.fingeprint`\n\n'\
	      ' Image Metadata Service (C) 2015')
	sys.exit(1)

target = sys.argv[1]
fp = sys.argv[2] if len(sys.argv) > 2 else 0

key_config = {
  'name_real': 'Image Metadata Service ISV',
  'name_email': 'ims@isv.com',
  'key_type': 'RSA',
  'key_length': 4096,
  'key_usage': '',
  'subkey_type': 'RSA',
  'subkey_length': '4096',
  'subkey_usage': 'auth,sign',
  'passphrase': '6154c62482c5bfe82c25eb596dfc93d006f4e0aea8ecdd8a4ea2cfcd3155039b'
}
gpg = gnupg.GPG(gnupghome='ims')

def find_fingerprint(g, fp):
	for k in g.list_keys():
		if k['fingerprint'] == fp:
			return k
	return None

def create_key(g, config):
	key_input = g.gen_key_input(**config)
	k = g.gen_key(key_input)
	if not k:
		print('Unable to generate key')
	if not k.fingerprint:
		print('Bad key fingerprint')
	return k.fingerprint

def ensure_fingerprint(g, config, fp):
	key = find_fingerprint(g, fp)
	if not key:
		key = find_fingerprint(
			g,
			create_key(g, config)
		)
		assert key
		with open('key.fingerprint', 'w') as f:
			f.write(key['fingerprint'])
	return key['fingerprint']

def sign_file(g, fl, fp, pp):
	key = find_fingerprint(g, fp)

	s = g.sign_file(
		fl,
		keyid=key['subkeys'][0][0],
		passphrase=pp,
		detach=True
	)

	return s

def sign_file_path(g, path, fp, pp):
	signature = sign_file(
		g,
		open(path),
		fp,
		pp
	)

	sigpath = path + '.asc'
	with open(sigpath, 'w') as f:
		f.write(str(signature))
	
	return signature

def verify_file_path(g, p):
	v = g.verify_data(
		p + '.asc',
		open(p).read()
	)
	return v

fp = ensure_fingerprint(gpg, key_config, fp)
for user in os.listdir(target):
	upath = os.path.join(target, user)
	for repo in os.listdir(upath):
		rpath = os.path.join(upath, repo, 'repodata.json')
		if not os.path.exists(rpath):
			continue
		r = sign_file_path(
			gpg,
			rpath,
			fp,
			key_config['passphrase']
		)
		assert r
		v = verify_file_path(
			gpg, 
			rpath
		)
		assert v.valid
		print(' - signed & verified: %s' % rpath)
