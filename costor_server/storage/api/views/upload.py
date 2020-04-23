from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404

from storage.models import UploadSession, DbFile, BackupSnapshot, BackupRoot, Object
from manager.models import Agent

import json

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_session(request):
    """
    Create new upload session
    :param request:
    :return:
    """
    if not all(key in request.data for key in ['parts', 'hash']):
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    agent = get_object_or_404(Agent, name=request.data['agent'])
    if request.user not in agent.users.all():
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    # check we don't already have this file
    if DbFile.objects.filter(id=request.data['hash']).exists():
        #print("Already seen this file, skipping")
        return Response(data=json.dumps(
            {
                "sessionid": None,
                "code": "seenbefore",
                "reason": "Already seen file with this hash"
            }
        ))

    session = UploadSession.objects.create(
        agent=agent,
        expectedparts=request.data['parts'],
        fullhash=request.data['hash'],
        timestamp=request.data['timestamp']
    )

    session.save()

    return Response(json.dumps({"sessionid": str(session.id)}))


@api_view(['POST'])
@parser_classes([MultiPartParser])
@permission_classes([permissions.AllowAny])
def append_to_session(request):
    if not all(key in request.data for key in ['session', 'sequenceno', 'hash']) and 'data' in request.FILES:
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    session = get_object_or_404(UploadSession, id=request.data['session'])

    if request.user not in session.agent.users.all():
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    session.append(request.FILES['data'], request.data['hash'], int(request.data['sequenceno']))

    if request.data['sequenceno'] == session.expectedparts:
        session.status = "C"

    if session.status is "C":
        return Response("Successfully uploaded file, all parts received")
    if session.status is "U":
        return Response("Received part.")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_status(request):
    session = get_object_or_404(UploadSession, id=request.data['session'])

    if request.user not in session.agent.users.all():
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    return Response(f'Session status: {session.status}, got {session.receivedparts} of {session.expectedparts}')

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_for_primes(request):
    if not 'primes' in request.data:
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    primes = request.data['primes'].split(',')

    results = []

    for objid in primes:
        r = DbFile.objects.filter(id=objid).exists()
        results.append((objid, r))

    res = json.dumps(results)

    #print(res)

    return Response(res)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_for_objects(request):
    if not 'objects' in request.data:
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    objects = request.data['objects'].split(',')

    results = []

    for objid in objects:
        r = Object.objects.filter(id=objid).exists()
        results.append((objid, r))

    res = json.dumps(results)

    #print(res)

    return Response(res)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@parser_classes([JSONParser])
def add_objects(request):
    r = request.data

    if not all(key in ['agent', 'objects', 'root'] for key in request.data):
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    agent = get_object_or_404(Agent, name=r['agent'])
    if request.user not in agent.users.all():
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    snapshots = BackupSnapshot.objects.filter(root__path=request.data['root'])

    snapshotids = {}

    for snap in snapshots:
        snapshotids[snap.seqno] = snap

    '''
    class Object(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    objhash = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=4096)
    type = models.CharField(max_length=4)
    stat = models.CharField(max_length=255)
    prime = models.ForeignKey(DbFile, on_delete=models.CASCADE, null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name="children")
    snapshot = models.ForeignKey(BackupSnapshot, related_name="backup_objects", on_delete=models.CASCADE, null=True)
    '''

    for o in request.data['objects']:
        print(o)

        snapshots = []
        for s in o['snapshots'][0]:
            snapshots.append(snapshotids.get(s))

        print(o['type'])

        if o['type'] == 'file':
            prime = DbFile.objects.get(id=o['prime'])
        else:
            prime = None

        if 'parent' in o:
            parent = Object.objects.get(id=o['parent'])
        else:
            parent = None

        dobj = Object.objects.create(
                id=o['id'],
                objhash=o['hash'],
                name=o['name'],
                path=o['path'],
                type=o['type'],
                stat=o['stat'],
                parent=parent,
                prime=prime
        )

        dobj.snapshots.set([snapshotids[x] for x in o['snapshots'][0]])

    return Response("DONE")


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def add_snapshot(request):

    print(request.data)

    # if not all(key in ['agent', 'timestamp', 'root', 'id', 'parent'] for key in request.data):
    #     raise APIException(
    #         detail="Missing parameters",
    #         code=400
    #     )

    agent = get_object_or_404(Agent, name=request.data['agent'])
    if not agent:
        raise APIException(
            detail="Agent doesn't exist",
            code=400
        )

    root = BackupRoot.objects.filter(path=request.data['root'], agent=request.data['agent'])

    if not root.exists():
        root = BackupRoot.objects.create(
            agent=agent,
            path=request.data['root']
        )
        root.save()
    else:
        root = root.first()

    if int(request.data['parent']) > 0:
        print(request.data['parent'])
        parent = BackupSnapshot.objects.filter(agent=request.data['agent'], seqno=request.data['parent'])
        if not parent.exists():
            raise APIException(
                detail="Parent snapshot doesn't exist",
                code=400
            )
        parent = parent.first()
    else:
        parent = None

    snapshot = BackupSnapshot.objects.create(
        seqno=request.data['id'],
        agent=agent,
        timestamp=request.data['timestamp'],
        root=root,
        parent=parent,
        rootobj=request.data['rootobj']
    )

    return Response(snapshot.id)
