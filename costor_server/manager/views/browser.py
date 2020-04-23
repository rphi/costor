from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from manager.models import Agent
from storage.models import BackupRoot, BackupSnapshot, Object


def home(request):
    return render(request, 'manager/home.html')


def agents(request):
    agents = Agent.objects.all()
    return render(request, 'manager/agents.html', {'agents': agents})


def agent(request, name):
    agent = get_object_or_404(Agent, name=name)

    roots = BackupRoot.objects.filter(agent=agent)

    return render(request, 'manager/agent.html', {'agent': agent, 'roots': roots})


def snapshots(request, root):
    root = get_object_or_404(BackupRoot, id=root)

    snaps = BackupSnapshot.objects.filter(root=root)

    return render(request, 'manager/snapshots.html', {'root': root, 'snaps': snaps})


def tree(request, snapshot):
    snap = get_object_or_404(BackupSnapshot, id=snapshot)
    rootobj = get_object_or_404(Object, id=snap.rootobj)

    return render(request, 'manager/snapshot.html', {'snap': snap, 'node': rootobj})
