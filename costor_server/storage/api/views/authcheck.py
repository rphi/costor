from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework.decorators import parser_classes
from django.shortcuts import get_object_or_404

from manager.models import Agent


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def auth_check(request):
    if not request.user.is_authenticated:
        raise APIException(
            detail="You aren't authenticated.",
            code=403
        )

    print(request.GET)
    if 'agent' not in request.GET:
        return Response(f'Authenticated as {request.user.username} with no agent')

    agent = Agent.objects.filter(name=request.GET['agent'])

    if not agent.exists():
        raise APIException(
            detail="Can't find that agent",
            code=404
        )

    agent = agent.first()

    if request.user not in agent.users.all():
        raise APIException(
            detail=f'Authenticated as {request.user.username} but you don\'t have permission for agent {agent.name}',
            code=403
        )

    return Response(f'Authenticated as {request.user.username} for agent {agent.name}')
