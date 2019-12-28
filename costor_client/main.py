import hasher
import config
import os
from db import Db
from pony.orm import Database as ponyDb
import json


def fullbackup(htm: hasher.HashTreeMaker,
               currentsnapshot: Db.Snapshot,
               conf, db: Db):
    print("✏️ Writing filesystem state to database")

    dirobjects = htm.getdirobjects()
    # NOTE:
    # dirobjects is an ordered dict, generated in bottom up order
    # when scanning the directory structure. Safe to assume dependencies
    # for foreign keys will be met

    for k, o in dirobjects.items():
        db.addObject(o, k, currentsnapshot)

    return


def incrementalbackup(htm: hasher.HashTreeMaker,
                      currentsnapshot: Db.Snapshot,
                      lastsnapshot: Db.Snapshot,
                      config, db: ponyDb):
    print("🔍 Looking for new + changed files...")
    print("   (this might take a moment)")
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
    print("   filesources: %i, dirobjects: %i" % (len(htm.getfilesources()), len(htm.getdirobjects())))

    '''
    Check for changes in local metadata DB
    '''
    print("\n============== CHECKING LOCAL DB FOR CHANGES ===============  ")
    db = Db(conf)
    db.init()
    root = db.getorcreateroot(conf.opts['root'])
    lastsnapshot = db.getlatestsnapshot(root)
    if not lastsnapshot:
        print("❌ Can't find any old completed snapshots")
        print("-> Initializing full backup")
        snapshot = db.createstandalonesnapshot(root)
        fullbackup(htm, snapshot, conf, db)
    else:
        snapshot = db.createincrementsnapshot(root, lastsnapshot)
        incrementalbackup(htm, snapshot, lastsnapshot, conf, db)

    print("✅ Successfully finished local bookkeeping")

    '''
    Sync with CoStor Server
    '''
    print("\n============== SYNCING WITH COSTOR SERVER ===============  ")
    print("🔗 Connecting to server at %s with agent ID '%s'" % (conf.opts['server'], conf.opts['agentid']))
    print("👍 Authentication success to CoStor")
    print("⬆️ Begin pushing data to server:")
    print("-> Pushing metadata changes")
    print("-> Pushing file blobs")
    print("✅ Successfully synced with server")

    print("\n============== COMPLETE ===============  ")
    print("All done!")

main()
