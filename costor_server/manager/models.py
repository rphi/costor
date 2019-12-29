from django.db import models
import uuid
import storage.models


# Create your models here.

class Agent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30)
    comment = models.TextField(max_length=120)


class File(models.Model):
    stat = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    data = models.ForeignKey(storage.models.DbFile)


class Directory(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=4096)
    stat = models.CharField(max_length=255)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name="child_dirs")
    files = models.ForeignKey


class Snapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    root = models.ForeignKey(Directory, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_created=True)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
