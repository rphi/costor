from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.decorators import parser_classes
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404

from storage.models import UploadSession, DbFile
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
        r = DbFile.objects.filter(id=objid).exists()
        results.append((objid, r))

    res = json.dumps(results)

    #print(res)

    return Response(res)


@api_view(['POST'])
@parser_classes([JSONParser])
@permission_classes([permissions.AllowAny])
def add_objects(request):
    r = request.data

    agent = get_object_or_404(Agent, name=r['agent'])
    if request.user not in agent.users.all():
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    for object in r['objects']:
        if not [''] in object:
            return

    return
