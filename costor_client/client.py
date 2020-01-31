from typing import List
from db import Db
from pony.orm import db_session
from config import Config

from math import ceil
from tqdm import tqdm
from time import sleep
import requests
import json
import os
import hashlib

class ServerClient:
    def __init__(self, conf: Config, db: Db):
        self.agentid = conf.opts['agentid']
        self.server = conf.opts['server']
        self.authtoken = conf.opts['authtoken']
        self.db = db

    def post(self, path, body, files=None):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
        body['agent'] = self.agentid
        r = requests.post(url=queryurl, headers=headers, data=body, files=files)
        return r

    def get(self, path, params=None):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
        r = requests.get(url=queryurl, headers=headers, params=params)
        return r

    def auth(self):
        # TODO: test authentication with server
        print("🔗 Connecting to server at %s with agent ID '%s'" %
              (self.server, self.agentid))

        payload = {'agent': self.agentid}
        r = self.get('storage/api/authcheck', params=payload)
        print(r)
        print(r.text)
        if r.status_code is not 200:
            raise Exception('Authentication failure')

        print("👍 Authentication success to CoStor")
        return True

    def queryprimes(self, primehashes: List[str]) -> List[str]:
        print("🔍 Looking for existing file primes on server")

        r = self.post('storage/api/upload/checkforprimes', body={'primes': ','.join(primehashes)})

        results = json.loads(r.json())

        missing = []
        for (primehash, exists) in results:
            if not exists:
                missing.append(primehash)

        print("-> Found %i of %i primes already backed up ([n] saving)" % (len(primehashes) - len(missing), len(primehashes)))
        missingprimehashes = primehashes
        print("-> need to upload %i primes" % len(missingprimehashes))
        return missingprimehashes

    def pushprime(self, prime: Db.Prime):
        # TODO push prime to server using large file upload protocol

        # split prime into 100MB chunks
        chunksize = 1048576 * 100
        primepath = self.db.get_prime_path(prime).path
        primehash = self.db.get_prime_hash(prime)

        primesize = os.path.getsize(primepath)

        chunkcount = ceil(primesize / chunksize)

        print("Prime at path %s is %i bytes, needs %i chunks" % (primepath, primesize, chunkcount))

        r = self.post('storage/api/upload/new', body={'parts': chunkcount, 'hash': primehash})

        result = json.loads(r.json())

        prog = tqdm(desc='Uploading chunks.', total=chunkcount, unit='*100MB')

        sequenceno = 0

        with open(primepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunksize), b""):
                hash_sha1 = hashlib.sha1()
                hash_sha1.update(chunk)
                chunkhash = hash_sha1.hexdigest()

                sequenceno += 1

                self.post('storage/api/upload/append',
                          body={
                              'session': result['sessionid'],
                              'sequenceno': sequenceno,
                              'hash': chunkhash
                               },
                          files={
                              'data': chunk
                          }
                          )
                prog.update()

        prog.close()
        return

    def pushobjects(self, objects: List[Db.Object]):
        # TODO push object metadata to server using single JSON payload
        return objects

    def queryobjects(self, objectids: List[str]) -> List[str]:
        print("🔍 Looking for existing object definitions on server")
        # TODO make request to server with list of IDs, querying for missing entries

        print("-> Found [n] of [n] objects already backed up ([n]% saving)")
        missingobjectids = objectids
        print("-> need to upload %i objects" % len(missingobjectids))
        return missingobjectids
