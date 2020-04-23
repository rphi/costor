from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from costor_server.settings import MEDIA_ROOT
from storage.models import UploadSession, DbFile, BackupSnapshot, BackupRoot, Object
from manager.models import Agent

import os
import shutil
import subprocess


def get_backup(request, snapshot):
    snap = get_object_or_404(BackupSnapshot, id=snapshot)

    rootobj = get_object_or_404(Object, id=snap.rootobj)
    root = snap.root.path

    workdir = '/tmp/costordownloads/'

    if not os.path.exists(workdir):
        print('crating costordownloads temp dir')
        try:
            os.mkdir(workdir)
        except Exception as e:
            raise e

    if os.path.exists(workdir + str(snap.id) + '.tar.bz2'):
        print('existing archive found, using that')
        with open(workdir + str(snap.id) + '.tar.bz2', "rb") as fsock:
            return HttpResponse(fsock.read(), content_type='application/x-tar')


    if os.path.exists(workdir + str(snap.id)):
        print("already got this snap in temp, nuking old dir")
        rm_r(workdir + str(snap.id))
        return HttpResponse('nuked')

    try:
        os.mkdir(workdir + str(snap.id))
    except Exception as e:
        raise e

    print("created temporary directory")

    # copy root object to temp

    print("creating root dir of snapshot")
    print(rootobj.name)

    stat = parse_statresult(rootobj.stat)

    try:
        os.mkdir(workdir + str(snap.id) + '/' + rootobj.name, stat['st_mode'])
        os.chown(workdir + str(snap.id) + '/' + rootobj.name, stat['st_uid'], stat['st_gid'])
    except Exception as e:
        raise e

    for c in rootobj.children.all():
        process_tree(workdir + str(snap.id) + '/' + rootobj.name, c)

    print('rebuilt snapshot')

    print('creating archive')

    subprocess.call(['tar', '-czf', workdir + str(snap.id) + '.tar.bz2', '-C', workdir + str(snap.id), '.'])

    print('archive built, clearing temp uncompressed tree')

    rm_r(workdir + str(snap.id))

    print('done')

    with open(workdir + str(snap.id) + '.tar.bz2', "rb") as fsock:
        return HttpResponse(fsock.read(), content_type='application/x-tar')


def process_tree(treedir: str, o: Object):
    print(o.path)

    objecttemppath = treedir + '/' + o.name
    stat = parse_statresult(o.stat)

    if o.type == 'file':
        realpath = MEDIA_ROOT + o.prime.data.name
        print(realpath)

        shutil.copyfile(realpath, objecttemppath)

    if o.type == 'dir':
        os.mkdir(objecttemppath, stat['st_mode'])

        for c in o.children.all():
            process_tree(objecttemppath, c)

    os.chown(objecttemppath, stat['st_uid'], stat['st_gid'])

    return


# https://stackoverflow.com/a/32881474/2491112
def rm_r(path):
    if not os.path.exists(path):
        return
    if os.path.isfile(path) or os.path.islink(path):
        os.unlink(path)
    else:
        shutil.rmtree(path)


def parse_statresult(stat: str):
    stat = stat.split('(')[1].split(')')[0].split(', ')

    d = {}

    for s in stat:
        s = s.split('=')
        d[s[0]] = int(s[1])

    return d
