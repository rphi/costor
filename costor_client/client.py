from typing import List
from db import Db
from config import Config

from tqdm import tqdm
from time import sleep
import requests


class ServerClient:
    def __init__(self, conf: Config):
        self.agentid = conf.opts['agentid']
        self.server = conf.opts['server']
        self.authtoken = conf.opts['authtoken']

    def post(self, path, body, files=None):
        queryurl = self.server + path
        headers = {'Authorization': f'Token {self.authtoken}'}
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

    def queryprimes(self, primeids: List[str]) -> List[str]:
        print("🔍 Looking for existing file primes on server")
        # TODO make request to server with list of IDs, querying for missing entries

        print("-> Found [n] of [n] primes already backed up ([n]% saving)")
        missingprimeids = primeids
        print("-> need to upload %i primes" % len(missingprimeids))
        return missingprimeids

    def pushprime(self, prime: Db.Prime):
        # TODO push prime to server using large file upload protocol
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
