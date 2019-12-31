from typing import List

import hasher
import config
from client import ServerClient
import os
from db import Db
from pony.orm import Database as ponyDb
from tqdm import tqdm
from time import sleep


def writedirobjs(htm: hasher.HashTreeMaker,
               currentsnapshot: Db.Snapshot,
               conf, db: Db):

    print("✏️ Writing metadata to database")
    sleep(0.2)

    dirobjects = htm.getdirobjects()
    # NOTE:
    # dirobjects is an ordered dict, generated in bottom up order
    # when scanning the directory structure. Safe to assume dependencies
    # for foreign keys will be met

    total, newentries = db.bulkaddobject(dirobjects, currentsnapshot)

    db.finalizesnapshot(currentsnapshot)

    print("✅ Successfully finished local bookkeeping")
    print("   Written %i Objects (%i already in DB)" % (total, total - newentries))
    return


def pushmeta(objects: [Db.Object], client: ServerClient) -> List[Db.Object]:
    objectids = [o.id for o in objects]
    missingobjectids = client.queryobjects(objectids)
    missingobjects = [o for o in objects if o.id in missingobjectids]

    client.pushobjects(objects)


    print("✅ Upload of metadata objects complete")
    return missingobjects


def pushprimes(primes: [Db.Prime], client: ServerClient):
    primeids = [p.id for p in primes]
    missingprimeids = client.queryprimes(primeids)
    missingprimes = [p for p in primes if p.id in missingprimeids]

    print("📦 Pushing missing file primes to server (this may take some time)")

    sleep(0.2)
    items = tqdm(missingprimes, desc="Processing: ", unit=" items", dynamic_ncols=True, leave=True)
    for p in items:
        client.pushprime(p)
        sleep(0.001)
    items.close()
    sleep(0.2)

    print("✅ Upload of primes complete")
    return


def main():
    conf = config.Config()
    print("CoStor Client, startup.")

    '''
    Get new hashes for filesystem
    '''
    print("\n============== UPDATING HASHES ===============  ")
    print("🧮 Building hash tables for tree with root at %s" % conf.opts['root'])
    htm = hasher.HashTreeMaker()
    htm.make(conf.opts['root'])
    print("✅ Successfully generated hashdb.")
    print("   dirobjects: %i" % len(htm.getdirobjects()))

    '''
    Check for changes in local metadata DB
    '''
    print("\n============== IDENTIFYING CHANGES ===============  ")
    db = Db(conf)
    db.init()
    root = db.getorcreateroot(conf.opts['root'])
    lastsnapshot = db.getlatestsnapshot(root)
    if not lastsnapshot:
        print("❌ Can't find any old completed snapshots")
        print("-> Initializing full backup")
        snapshot = db.createstandalonesnapshot(root)
    else:
        print("-> Continuing with incremental backup")
        snapshot = db.createincrementsnapshot(root, lastsnapshot)
    writedirobjs(htm, snapshot, conf, db)

    '''
    Sync with CoStor Server
    '''
    print("\n============== SYNCING WITH COSTOR SERVER ===============  ")
    client = ServerClient(conf)
    client.auth()

    print("⬆️ Begin pushing data to server:")

    print("-> Gathering fresh metadata objects")
    objects = db.getobjectsforsnapshot(snapshot)
    pushedobjects = pushmeta(objects, client)

    print("-> Gathering primes to sync")
    primes = db.getprimesforobjects(pushedobjects)
    pushprimes(primes, client)

    print("✅ Successfully synced with server")

    print("\n============== COMPLETE ===============  ")
    print("All done!")


def test():
    conf = config.Config()
    client = ServerClient(conf)
    client.auth()


#main()
test()
