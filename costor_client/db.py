from tokenize import String
from typing import Dict, List

from pony.orm import *
from datetime import datetime
from config import Config
from hasher import DirObject, sha1str
from tqdm import tqdm
from time import sleep

DEBUG = False


def printd(str):
    if DEBUG:
        print(str)


class Db:
    db = Database()

    def __init__(self, conf: Config):
        self.conf = conf

    class BackupRoot(db.Entity):
        id = PrimaryKey(int, auto=True)
        path = Required(str)
        snapshots = Set('Snapshot', reverse='root')

    # a specific run of this application
    class Snapshot(db.Entity):
        id = PrimaryKey(int, auto=True)
        timestamp = Required(datetime)
        complete = Required(bool)
        synced = Required(bool)
        objects = Set('Object', reverse='snapshots')
        root = Required('BackupRoot', reverse='snapshots')
        topobject = Optional('Object', reverse='topobjectfor')
        parent = Optional('Snapshot', reverse='child')
        child = Optional('Snapshot', reverse='parent')
        primes = Set('Prime', reverse='snapshots')

    # anything included in the backup tree
    # type can be "file" or "dir" (or "sym")
    class Object(db.Entity):
        id = PrimaryKey(str)  # sha(path+hash)
        hash = Required(str)
        name = Required(str)
        prime = Optional('Prime', reverse='objects')
        path = Required(str)
        type = Required(str)
        stat = Required(str)
        children = Set('Object', reverse='parent')
        parent = Optional('Object', reverse='children')
        snapshots = Set('Snapshot', reverse='objects')
        topobjectfor = Optional('Snapshot')
        depth = Required(int)

    # file path to object hash mappings
    class Prime(db.Entity):
        filehash = PrimaryKey(str)
        paths = Set('Path', reverse='target')
        firstseen = Required(datetime, sql_default='CURRENT_TIMESTAMP')
        lastseen = Required(datetime, sql_default='CURRENT_TIMESTAMP')
        objects = Set('Object', reverse='prime')
        snapshots = Set('Snapshot', reverse=None)

    class Path(db.Entity):
        target = Required('Prime', reverse='paths')
        path = Required(str)
        valid = Required(bool, auto=True)
        timestamp = Required(datetime, sql_default='CURRENT_TIMESTAMP')

    def init(self):
        print('-> Initializing local metadata database')
        self.db.bind(provider='sqlite', filename='costor_client.sqlite', create_db=True)
        self.db.generate_mapping(create_tables=True)
        print("✅ DB up and running")

    @db_session
    def getorcreateroot(self, path):
        root = self.BackupRoot.get(path=path)
        if root:
            print("-> Found existing BackupRoot")
            return root

        root = self.BackupRoot(path=path)
        print("✨ Created new BackupRoot for %s" % self.conf.opts['root'])
        return root

    @db_session
    def getlatestsnapshot(self, root: BackupRoot):
        snapshot = select(s for s in self.Snapshot if s.root is root and s.complete).order_by(
            desc(self.Snapshot.timestamp))[:1]
        if not snapshot:
            return False
        snapshot = snapshot[0]
        print("-> Found previous snapshot metadata")
        print("📅 Last completed update was at " + str(snapshot.timestamp))
        return snapshot

    @db_session
    def createstandalonesnapshot(self, root: BackupRoot):
        snapshot = self.Snapshot(
            timestamp=datetime.now(),
            complete=False,
            synced=False,
            root=root.id
        )
        flush()
        print("✨ Created new standalone backup snapshot for this session (ID: %i)" % snapshot.id)
        return snapshot

    @db_session
    def createincrementsnapshot(self, root: BackupRoot, parent: Snapshot):
        snapshot = self.Snapshot(
            timestamp=datetime.now(),
            complete=False,
            synced=False,
            root=root.id,
            parent=parent.id
        )
        flush()
        print("✨ Created new incremental backup snapshot for this session (ID: %i)" % snapshot.id)
        return snapshot

    @db_session
    def finalizesnapshot(self, s: Snapshot):
        self.Snapshot[s.id].complete = True
        print("-> finalized snapshot")

    @db_session
    def __create_path(self, path: str, target: Prime):
        path = self.Path(
            path=path,
            target=target,
            valid=True
        )
        return path

    @db_session
    def set_top_object(self, objid, snapshot: Snapshot):
        ss = self.Snapshot.get(id=snapshot.id)
        ss.topobject = self.Object.get(id=objid)
        return

    @db_session
    def addobject(self, obj: DirObject, objectid: str, s: Snapshot) -> (Object, bool):
        objhash = obj.gethash()
        if obj.type is "dir":
            eobj = self.Object.get(id=objectid)
            if eobj:
                printd("-> found matching hash for obj in DB, attaching to snapshot")
                eobj.snapshots.add(self.Snapshot[s.id])
                return eobj, False
            nobj = self.Object(
                id=objectid,
                hash=objhash,
                name=obj.name,
                path=obj.path,
                prime=None,
                type="dir",
                stat=str(obj.stat),
                # can't set parent, as parent may not exist in DB yet,
                # - parent will be assigned through reverse when children
                # attached.
                snapshots=self.Snapshot[s.id],
                depth=obj.depth
            )
            if obj.children:
                try:
                    nobj.children.add([self.Object[k] for k in obj.children])
                except ObjectNotFound as e:
                    raise Exception("Child object not found")
            printd("-> created new Object for dir at %s with %i children"
                   % (obj.path, len(obj.children)))

            return nobj, True

        elif obj.type is "file":
            eobj = self.Object.get(id=objectid)
            if eobj:
                printd("-> found matching hash for obj in DB, attaching to snapshot")
                eobj.snapshots.add(self.Snapshot[s.id])
                return eobj, False
            primeobj, new = self.addprime(obj.path, objhash, s)
            nobj = self.Object(
                id=objectid,
                hash=objhash,
                name=obj.name,
                path=obj.path,
                prime=primeobj,
                type="file",
                stat=str(obj.stat),
                snapshots=self.Snapshot[s.id],
                depth=obj.depth
            )

            printd("-> created new Object for file at %s" % obj.path)
            return nobj, True

    @db_session
    def addprime(self, path: str, hash: str, snapshot: Snapshot) -> (Prime, bool):
        printd("-> adding prime for path %s" % path)
        eobj = self.Prime.get(filehash=hash)
        if eobj:
            printd("-> found matching prime in DB")
            epath = select(p for p in eobj.paths if p.path == path)
            if epath.exists:
                printd("-> path already mapped to prime")
            else:
                printd("-> path not mapped to prime, adding")
                npath = self.__create_path(path=path, target=eobj)
            eobj.lastseen = datetime.now()
            eobj.snapshots.add(self.Snapshot[snapshot.id])
            return eobj, False
        printd("-> creating new prime in DB")
        obj = self.Prime(
            filehash=hash,
            firstseen=datetime.now(),
            lastseen=datetime.now()
        )
        npath = self.__create_path(path=path, target=obj)
        printd("-> invalidating any other primes attached to this path")
        epaths = select(p for p in self.Path if p.target != obj and p.path == path)
        for p in epaths:
            p.valid = False
        obj.snapshots.add(self.Snapshot[snapshot.id])
        return obj, True

    @db_session
    def getobjectsforsnapshot(self, snapshot: Snapshot) -> [Object]:
        return select(o for o in self.Object if snapshot in o.snapshots).order_by(self.Object.depth).fetch()

    @db_session
    def getprimesforobjects(self, objects: [Object]) -> [Prime]:
        return [o.prime for o in objects if o.prime is not None]

    @db_session
    def bulkaddobject(self, dirobjs: Dict[str, DirObject], currentsnapshot: Snapshot):
        # fairly sure this method means we share a db_session for the entire import, which
        # speeds things up somewhat..

        # setup progress bar
        sleep(0.2)
        items = tqdm(dirobjs.items(), desc="Writing: ", unit=" entries", dynamic_ncols=True, leave=True)
        newentries = 0

        for k, o in items:
            _, new = self.addobject(o, k, currentsnapshot)
            if new:
                newentries += 1

        items.close()
        sleep(0.2)  # allow progress bar to sort itself out
        return newentries, len(dirobjs)

    @db_session
    def get_prime_hash(self, prime: Prime):
        return prime.filehash

    @db_session
    def get_prime_path(self, prime: Prime):
        path = select(p for p in prime.paths if p.valid).order_by(desc(self.Path.timestamp))
        return path.first()

    @db_session
    def get_prime_timestamp(self, prime: Prime):
        p = self.Prime.get(filehash=prime.filehash)
        return p.firstseen

    @db_session
    def dump_snapshot(self, snapshot: Snapshot, tree=False):
        """
        Get a json.dumps compatible representation of a snapshot

        :param snapshot:
        :param tree: bool for if tree is to be included in dump, default false
        :return: json serialisable object
        """

        ss = self.Snapshot.get(id=snapshot.id)

        dump = {
            'id': ss.id,
            'timestamp': str(ss.timestamp),
            'root': ss.root.id
        }

        if tree:
            dump['tree'] = self.build_tree_from_object(ss.topobject)

        if ss.child:
            dump['child'] = ss.child.id

        if ss.parent:
            dump['parent'] = ss.parent.id

        return dump

    @db_session
    def build_tree_from_object(self, top: Object):
        tree = {
            'id': top.id,
            'hash': top.hash,
            'name': top.name,
            'path': top.path,
            'type': top.type,
            'stat': top.stat,
        }

        if top.prime:
            tree['prime'] = top.prime.filehash

        if top.children:
            tree['children'] = []

            for obj in top.children:
                tree['children'].append(self.build_tree_from_object(obj))

        return tree

    @db_session
    def dump_objects(self, objects: [Object]):
        """
        This is a flatter version of dump_snapshot, that dumps a basic object containing
        a representation of the objects given as the parameter, ready to be json stringified

        :param objects:
        :return dump:
        """
        objs = [o for o in objects]

        dump = []

        for o in objs:
            data = {
                'id': o.id,
                'hash': o.hash,
                'name': o.name,
                'path': o.path,
                'type': o.type,
                'stat': o.stat,
                'children': [],
                'snapshots': [],
                'depth': o.depth
            }

            if o.prime:
                data['prime'] = o.prime.filehash

            if o.parent:
                data['parent'] = o.parent.id

            data['children'].append(self.get_ids(self.Object.get(id=o.id).children))
            data['snapshots'].append(self.get_ids(self.Object.get(id=o.id).snapshots))

            dump.append(data)

        return dump

    @db_session
    def get_ids(self, objects: [Object]) -> [String]:
        return [o.id for o in objects]

    @db_session
    def get_root_path(self, root: BackupRoot) -> String:
        return self.BackupRoot.get(id=root.id).path
