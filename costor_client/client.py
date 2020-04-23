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

    def post(self, path, body, files=None, addagent=True):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
        if addagent:
            body['agent'] = self.agentid
        r = requests.post(url=queryurl, headers=headers, data=body, files=files)
        return r

    def postjson(self, path, data):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
        data['agent'] = self.agentid
        r = requests.post(url=queryurl, headers=headers, json=data)
        return r

    def get(self, path, params=None):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
        r = requests.get(url=queryurl, headers=headers, params=params)
        return r

    def auth(self):
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
        if r.status_code is not 200:
            raise Exception('API error')

        results = json.loads(r.json())

        missing = []
        for (primehash, exists) in results:
            if not exists:
                missing.append(primehash)

        print("-> Found %i of %i primes already backed up (%i%% saving)" % (
        len(primehashes) - len(missing), len(primehashes),
        int(((len(primehashes) - len(missing)) / min(-1, len(primehashes))) * 100)))
        missingprimehashes = missing
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

        # print("Prime at path %s is %i bytes, needs %i chunks" % (primepath, primesize, chunkcount))

        r = self.post('storage/api/upload/new', body={
            'parts': chunkcount,
            'hash': primehash,
            'timestamp': self.db.get_prime_timestamp(prime)
        })
        if r.status_code is not 200:
            raise Exception('API error')

        result = json.loads(r.json())

        if result['sessionid'] == None:
            if result['code'] == 'seenbefore':
                # print("Server has already seen this file, ignoring")
                return
            raise Exception("Unknown response from server when creating new session")

        # prog = tqdm(desc='Uploading chunks.', total=chunkcount, unit='*100MB')

        sequenceno = 0

        with open(primepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunksize), b""):
                hash_sha1 = hashlib.sha1()
                hash_sha1.update(chunk)
                chunkhash = hash_sha1.hexdigest()

                sequenceno += 1

                r = self.post('storage/api/upload/append',
                              body={
                                  'session': result['sessionid'],
                                  'sequenceno': sequenceno,
                                  'hash': chunkhash
                              },
                              files={
                                  'data': chunk
                              }
                              )
                if r.status_code is not 200:
                    raise Exception('API error')
                # prog.update()

        # prog.close()
        return

    def pushsnapshot(self, snapshot: Db.Snapshot):
        dump = self.db.dump_snapshot(snapshot, tree=False)
        dump['root'] = [self.db.get_root_path(snapshot.root)]
        dump['rootobj'] = [self.db.get_top_object_id(snapshot)]

        if 'parent' not in dump:
            dump['parent'] = [0]

        jdump = json.dumps(dump)

        with open('sdump.json', 'w') as outfile:
            outfile.write(jdump)

        print(dump)

        r = self.post('storage/api/upload/add_snapshot', body=dump)
        if r.status_code is not 200:
            print(r.text)
            raise Exception('API error')

        print(r.status_code)

        return

    def pushobjects(self, objects: List[Db.Object], snapshot: Db.Snapshot):
        dump = {
            'agent': self.agentid,
            'objects': self.db.dump_objects(objects),
            'root': self.db.get_root_path(snapshot.root)
        }

        with open('dump.json', 'w') as outfile:
            outfile.write(json.dumps(dump))

        r = self.postjson('storage/api/upload/add_objects', data=dump)
        if r.status_code is not 200:
            print(r.text)
            raise Exception('API error')

        return

    def attachobjects(self, objects: List[Db.Object], snapshot: Db.Snapshot):
        dump = {
            'agent': self.agentid,
            'objects': [o.id for o in objects],
            'root': self.db.get_root_path(snapshot.root),
            'snapshot': snapshot.id
        }

        r = self.postjson('storage/api/upload/attach_objects', data=dump)
        if r.status_code is not 200:
            print(r.text)
            raise Exception('API error')

        return

    def queryobjects(self, objectids: List[str]) -> List[str]:
        print("🔍 Looking for existing object definitions on server")

        r = self.post('storage/api/upload/checkforobjects', body={'objects': ','.join(objectids)})
        if r.status_code is not 200:
            raise Exception('API error')

        results = json.loads(r.json())

        missing = []
        needupdate = []
        for (objectid, exists) in results:
            if not exists:
                missing.append(objectid)
            else:
                needupdate.append(objectid)

        print("-> Found %i of %i objects already backed up (%i%% saving)" % (
            len(objectids) - len(missing), len(objectids),
            int((((len(objectids) - len(missing)) / len(objectids)) * 100)))
              )
        missingobjectids = missing
        print("-> need to upload %i objects (and update %i)" % (len(missingobjectids), len(needupdate)))
        return missingobjectids, needupdate
