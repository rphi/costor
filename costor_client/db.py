from pony.orm import *
from datetime import datetime
from config import Config
from hasher import DirObject

DEBUG = True


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
        parent = Optional('Snapshot', reverse='child')
        child = Optional('Snapshot', reverse='parent')

    # anything included in the backup tree
    # type can be "file" or "dir" (or "sym")
    class Object(db.Entity):
        hash = PrimaryKey(str)
        name = Required(str)
        path = Required(str)
        type = Required(str)
        stat = Required(str)
        children = Set('Object', reverse='parent')
        parent = Optional('Object', reverse='children')
        snapshots = Set('Snapshot', reverse='objects')

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
        print("-> Continuing with incremental backup")
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
        s.complete = True

    @db_session
    def addObject(self, obj: DirObject, objhash: str, s: Snapshot):
        if obj.type is "dir":
            eobj = self.Object.get(hash=objhash)
            if eobj:
                printd("-> found matching hash for obj in DB, attaching to snapshot")
                eobj.snapshots.add(s.id)
                return
            nobj = self.Object(
                hash=objhash,
                name=obj.name,
                path=obj.path,
                type="dir",
                stat=str(obj.stat),
                # can't set parent, as parent may not exist in DB yet,
                # - parent will be assigned through reverse when children
                # attached.
                snapshots=self.Snapshot[s.id]
            )
            if obj.children:
                try:
                    nobj.children.add([self.Object[k] for k in obj.children])
                except ObjectNotFound as e:
                    raise Exception("Child object not found")
            printd("-> created new Object for dir at %s with %i children"
                   % (obj.path, len(obj.children)))

        elif obj.type is "file":
            eobj = self.Object.get(hash=objhash)
            if eobj:
                printd("-> found matching hash for obj in DB, attaching to snapshot")
                eobj.snapshots.add(self.Snapshot[s.id])
                return
            nobj = self.Object(
                hash=objhash,
                name=obj.name,
                path=obj.path,
                type="file",
                stat=str(obj.stat),
                snapshots=self.Snapshot[s.id]
            )
            printd("-> created new Object for file at %s" % obj.path)
