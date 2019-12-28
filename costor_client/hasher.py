'''
costor_hasher
~~
A helper script to generate a directory tree with hashes of each directory and
all files contained within, used by the client to identify which files may have
changed since the last backup snapshot, and require to be re-added to the next
backup snapshot
'''

import os
import hashlib
from collections import OrderedDict

from scandir import scandir
from typing import Dict, List

DEBUG = False


def printd(str):
    if DEBUG:
        print(str)


def sha1file(fname):
    hash_sha1 = hashlib.sha1()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha1.update(chunk)
    return hash_sha1.hexdigest()


def sha1list(list):
    hash_sha1 = hashlib.sha1()
    hash_sha1.update(bytes("".join(list), encoding='utf-8'))
    return hash_sha1.hexdigest()


def sha1str(str):
    hash_sha1 = hashlib.sha1()
    hash_sha1.update(bytes(str, encoding='utf-8'))
    return hash_sha1.hexdigest()


class DirObject:
    # Initializer for directories
    def loaddir(self, name: str, path: str, stat: os.stat_result, children: List[str]):
        self.name = name
        self.path = path
        self.stat = stat
        self.type = "dir"
        self.children = children

    # Initializer for files
    def loadfile(self, name: str, path: str, stat: os.stat_result, filehash: str):
        self.name = name
        self.path = path
        self.stat = stat
        self.type = "file"
        self.hash = filehash

    def gethash(self):
        if self.type is "file":
            return self.hash
        elif self.type is "dir":
            shastring = self.name + self.path + str(self.stat)
            childhashes = str(sorted(self.children))
            return sha1str(shastring + childhashes)
        else:
            raise Exception("Unknown DirObject type %s" % self.type)


class HashTreeMaker:
    filesources = {}
    dirobjects = OrderedDict()
    topdirobj = None

    def __hashdir(self, name: str, path: str, stat: os.stat_result):
        childhashes = []
        for entry in scandir(path):
            printd('scandir item: %s' % entry.path)
            if entry.is_symlink():
                printd('\t item is SYMLINK, ignoring for now')
                # childhashes.append(filehash)
                # if filehash not in fileobjects:
                #     fileobjects[filehash] = entry.path
                #     printd("\t\tNew hash, adding to file store.")
                # else:
                #     printd("\t\tHash collision! Skipping.")
            elif entry.is_dir():
                inode = entry.inode()
                printd('\t item is DIRECTORY with inode %i, drilling down:' % inode)
                dirobj = self.__hashdir(entry.name, entry.path, entry.stat())
                objhash = dirobj.gethash()
                # add object to global dict
                self.dirobjects[objhash] = dirobj
                # link item as child to this dir
                childhashes.append(objhash)
            elif entry.is_file():
                filehash = sha1file(entry.path)
                printd('\t item is FILE with hash %s' % filehash)
                printd('\t\tCreating DirObject for file.')
                obj = DirObject()
                obj.loadfile(entry.name, entry.path, entry.stat(), filehash)
                # add object to global dict
                self.dirobjects[filehash] = obj
                # link item as child to this dir
                childhashes.append(filehash)
                # add file source hash->source mapping
                if filehash not in self.filesources:
                    self.filesources[filehash] = entry.path
                    printd("\t\tNew hash, adding to file mappings.")
                else:
                    printd("\t\tHash collision! Skipping.")
            else:
                raise Exception("Unknown file type")
        dirobject = DirObject()
        dirobject.loaddir(
            name=name,
            path=path,
            stat=stat,
            children=childhashes
        )
        dirhash = dirobject.gethash()
        printd('-> Completed dir %s, committing dirobject' % path)
        if dirhash not in self.dirobjects:
            self.dirobjects[dirhash] = dirobject
            printd("\t\tNew hash %s, adding to directory store." % dirhash)
        else:
            printd("\t\tHash collision! Skipping.")
        return dirobject

    def make(self, path):
        if self.topdirobj:
            raise Exception("This has already been used.")
        stat = os.stat(path)
        name = path.split('/')[-1]
        self.topdirobj = self.__hashdir(name, path, stat)
        return self.topdirobj.gethash()

    def gettopobj(self) -> DirObject:
        return self.topdirobj

    def getfilesources(self) -> Dict[str, str]:
        return self.filesources

    def getdirobjects(self) -> Dict[str, DirObject]:
        return self.dirobjects
