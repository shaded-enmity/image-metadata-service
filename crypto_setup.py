#!/usr/bin/python -tt

import argparse, binascii, getpass, gnupg, hashlib, json, os, sys 

p = argparse.ArgumentParser()
p.add_argument('keyconfig', default=None)
p.add_argument('-g', '--gpg-homedir')

args = p.parse_args()

if not args.gpg_homedir:
        print("Please specify a GPG home dir with -g / --gpg-homedir")
        sys.exit(1)

def create_key(homedir, key_config):
        gpg = gnupg.GPG(gnupghome=homedir)
        key_input = gpg.gen_key_input(**key_config)
        k = gpg.gen_key(key_input)
        if not k:
                raise Exception('Unable to generate key')

        return k.fingerprint


class InputType(object):
        (NONE, TEXT, NUMBER, PASSWORD, EMAIL) = range(5)


InputValidators = [
        lambda x: False,
        lambda x: isinstance(x, str),
        lambda x: int(x, 0),
        lambda x: isinstance(x, str),
        lambda x: x.count('@') != 0
]               

def varbind(kd, name):
        def prop(value=None):
                if value:
                        setattr(kd, name, value)
                return getattr(kd, name)
        return prop

class KeyData(object):
        def __init__(self):
                self._name = 'Image Metadata Service - ISV'
                self._email = 'ims@isv.com'
                self._type = 'RSA'
                self._length = '4096'
                self._passphrase = ''

        @property
        def name(self):
                return self._name

        @property
        def email(self):
                return self._email

        @property
        def type(self):
                return self._type

        @property
        def length(self):
                return self._length

        @property
        def passphrase(self):
                return self._passphrase

class UserInput(object):
        def __init__(self, message, context, itype):
                self.message = message
                self.context = context
                self.input_type = itype

        def input(self):
                if self.input_type != InputType.PASSWORD:
                        i = raw_input(self.message + ' [%s]: ' % str(self.context()))
                        if i.strip() != '':
                                if InputValidators[self.input_type](i):
                                        self.context(i)
                                else:
                                        print('INVALID INPUT: %s Try again ...' % i)
                                        self.input()
                else:
                        i = getpass.getpass(self.message + ': ')
                        if InputValidators[self.input_type](i):
                                dk = hashlib.pbkdf2_hmac('sha256', i, os.urandom(len(i)*2), 100000)
                                self.context(binascii.hexlify(dk))

kd = KeyData()
Inputs = [
        UserInput('Enter key name',        varbind(kd, '_name'),        InputType.TEXT),
        UserInput('Enter email',           varbind(kd, '_email'),       InputType.EMAIL),
        UserInput('Enter key type',        varbind(kd, '_type'),        InputType.TEXT),
        UserInput('Enter key length',      varbind(kd, '_length'),      InputType.NUMBER),
        UserInput('Enter key passphrase',  varbind(kd, '_passphrase'),  InputType.PASSWORD)
]

for i in Inputs:
        i.input()

key_config = {
  'name_real': kd.name,
  'name_email': kd.email,
  'key_type': kd.type,
  'key_length': kd.length,
  'key_usage': '',
  'subkey_type': kd.type,
  'subkey_length': kd.length,
  'subkey_usage': 'auth,sign',
  'passphrase': kd.passphrase
}

fingerprint = create_key(args.gpg_homedir, key_config)

conf = {
        'gpg_homedir': args.gpg_homedir,
        'gpg_fingerprint': fingerprint,
        'gpg_passphrase': kd.passphrase
}

with open(args.keyconfig, 'w+') as fp:
        json.dump(conf, fp, indent=4)

print('Configuration saved in: %s [homedir: %s]' % 
        (os.path.abspath(args.keyconfig), 
        os.path.abspath(args.gpg_homedir))
)
