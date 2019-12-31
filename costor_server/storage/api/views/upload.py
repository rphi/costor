from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.decorators import parser_classes
from django.shortcuts import get_object_or_404

from storage.models import UploadSession, DbFile
from manager.models import Agent

import json

@api_view(['PUT'])
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

    agent = get_object_or_404(Agent, id=request.data['agent'])
    if request.user not in agent.users:
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    session = UploadSession.objects.create(
        agent=agent,
        totalparts=request.data['parts'],
        sessionhash=request.data['hash'],
    )

    session.save()

    return Response(f"Upload session created with ID: {session.id}")


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

    if request.user not in session.agent.users:
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    session.append(request.FILES['data'], request.data['hash'], request.data['sequenceno'])

    if session.status is "C":
        return Response("Successfully uploaded file, all parts received")
    if session.status is "U":
        return Response("Received part.")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_status(request):
    session = get_object_or_404(UploadSession, id=request.data['session'])

    if request.user not in session.agent.users:
        raise APIException(
            detail="You don't have permission to work on this agent",
            code=403
        )

    return Response(f'Session status: {session.status}, got {session.receivedparts} of {session.expectedparts}')

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def check_for_object(request):
    if not 'objects' in request.data:
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    results = {}

    for objid in request.data['objects']:
        r = DbFile.objects.filter(id=objid).exists()
        results[objid] = r

    return json.dumps(results)
