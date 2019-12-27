from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.decorators import parser_classes
from django.shortcuts import get_object_or_404
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

import json
import hashlib

from storage.models import UploadPackage, UploadSession, DbFile
from manager.models import Agent


@api_view(['PUT'])
@permission_classes([permissions.AllowAny])
def create_session(request):
    """
    Create new upload session
    :param request:
    :return:
    """
    if not all(key in request.data for key in ['agent', 'parts', 'hash', 'identifier']):
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    agent = get_object_or_404(Agent, id=request.data['agent'])

    session = UploadSession.objects.create(
        agent=agent,
        identifier=request.data['identifier'],
        totalparts=request.data['parts'],
        sessionhash=request.data['hash'],
        status="N"
    )

    session.save()

    return Response(f"Upload session created with ID: {session.id}")


@api_view(['POST'])
@parser_classes([MultiPartParser])
@permission_classes([permissions.AllowAny])
def append_to_session(request):
    if not all(key in request.data for key in ['session', 'sequenceno', 'hash', 'file']):
        raise APIException(
            detail="Missing parameters",
            code=400
        )

    session = get_object_or_404(UploadSession, id=request.data['session'])

    if session.status == "N":
        session.status = "U"
    elif session.status != "U":
        return Response("Error session closed")

    if int(request.data['sequenceno']) >= session.totalparts:
        return Response("Package number out of range")

    package = UploadPackage.objects.filter(session=session, sequenceno=request.data['sequenceno'])

    if package.exists():
        return Response("Already recieved this package number")

    file = File(request.data['file'])
    hash = request.data['hash']

    md5 = hashlib.md5()
    for chunk in file.chunks():
        md5.update(chunk)
    md5sum = md5.hexdigest()

    if hash != md5sum:
        return Response(f"Hash mismatch, rejecting package, please try again. Expected {hash}, got {md5sum}")

    package = UploadPackage.objects.create(
        session=session,
        sequenceno=request.data['sequenceno'],
        data=request.data['file'],
        hash=hash,
        complete=True,
        valid=True
    )

    package.save()

    return Response("done")


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def finalise_package(request):
    """
    Mark package as complete and request verification
    :param request:
    :return:
    """

    if not 'session' in request.data:
        raise APIException(
            detail="Missing session ID",
            code=400
        )

    session = get_object_or_404(UploadSession, id=request.data['session'])

    if session.totalparts != session.packageparts.count():
        session.status = "E"
        session.save()
        return "Error missing packageparts"

    # create empty file to use in merge process

    storage = FileSystemStorage(location='media/storage/')

    with open(storage.location + '/' + session.sessionhash + '+' + session.identifier, 'w+b') as f:
        file = File(f)

        parts = session.packageparts.order_by('sequenceno').all()

        for part in parts:
            print(f"appending part {part.sequenceno} to file")
            file.write(part.data.read())
            print(f"append done, new size {len(file)}")

        file.close()
        file.open('r')

        md5 = hashlib.md5()
        # for chunk in file.chunks():
        #     md5.update(chunk)
        # md5sum = md5.hexdigest()

        if True: #md5sum == session.sessionhash:
            # upload was good
            fileobject = DbFile.objects.create(
                agent=session.agent,
                hash=session.sessionhash,
                data=file
            )
            fileobject.save()

            session.delete()

        else:
            return Response(f"Error merging file, mismatched hashes. Expected {session.sessionhash}, got {totalhash}")

    return Response("done")
