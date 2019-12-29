from typing import List
from db import Db
from config import Config

from tqdm import tqdm
from time import sleep


class ServerClient:
    def __init__(self, conf: Config):
        self.config = conf

    def auth(self):
        # TODO: test authentication with server
        print("🔗 Connecting to server at %s with agent ID '%s'" %
              (self.config.opts['server'], self.config.opts['agentid']))
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
