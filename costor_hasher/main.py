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
from scandir import scandir, walk, DirEntry
import json

fileobjects = {}
dirobjects = {}

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

def hashdir(name, path, stat):
    childhashes = {}
    for entry in scandir(path):
        print('scandir item: %s' % entry.path)
        if entry.is_symlink():
            print('\t item is SYMLINK, ignoring for now')
            # childhashes.append(filehash)
            # if filehash not in fileobjects:
            #     fileobjects[filehash] = entry.path
            #     print("\t\tNew hash, adding to file store.")
            # else:
            #     print("\t\tHash collision! Skipping.")
        elif entry.is_dir():
            inode = entry.inode()
            print('\t item is DIRECTORY with inode %i, drilling down:' % inode)
            dirhash = hashdir(entry.name, entry.path, entry.stat())
            childhashes[dirhash] = {
                "name": entry.name,
                "type": "dir"
            }
        elif entry.is_file():
            filehash = sha1file(entry.path)
            print('\t item is FILE with hash %s' % filehash)
            childhashes[filehash] = {
                "name": entry.name,
                "type": "file",
                "stat": entry.stat()
            }
            if filehash not in fileobjects:
                fileobjects[filehash] = entry.path
                print("\t\tNew hash, adding to file store.")
            else:
                print("\t\tHash collision! Skipping.")
        else:
            raise Exception("Unknown file type")
    print('-> Completed dir %s, committing dirobject' % path)
    dirobject = {
        "name": name,
        "path": path,
        "stat": stat,
        "childhashes": childhashes
    }
    dirhash = sha1str(json.dumps(dirobject, sort_keys=True))
    if dirhash not in dirobjects:
        dirobjects[dirhash] = dirobject
        print("\t\tNew hash, adding to directory store.")
    else:
        print("\t\tHash collision! Skipping.")
    return dirhash


# for dirName, subdirList, fileList in walk(rootdir, topdown=False):
#     print('Found directory: %s' % dirName)
#     hashdir(dirName)
rootdirobj = hashdir('costor', '/Users/rob/Documents/Projects/costor', os.stat('/Users/rob/Documents/Projects/costor'))

with open('files.json', 'w') as outfile:
    json.dump(fileobjects, outfile)

with open('dirs.json', 'w') as outfile:
    json.dump(dirobjects, outfile)

print('\t->->->COMPLETE<-<-<-')
# print('processed %i entries with %i collisions' % (total, collisions))
