import uuid

from django.db import models
from manager.models import Agent


# Create your models here.

class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    identifier = models.CharField(max_length=32)
    totalparts = models.IntegerField()
    sessionhash = models.CharField(max_length=32, blank=False, null=False)
    # package parts are stored in relatedfield packageparts
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1)
    # status can be "N": new, "U": uploading, "F": failed, "V": verfifying, "M": merging, "C": complete


class UploadPackage(models.Model):
    session = models.ForeignKey(UploadSession, on_delete=models.CASCADE, related_name="packageparts")
    hash = models.CharField(max_length=32, blank=False, null=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.FileField(upload_to="uploads")
    complete = models.BooleanField(default=False)
    valid = models.BooleanField(default=False)
    sequenceno = models.IntegerField()


class DbFile(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    hash = models.CharField(max_length=32, blank=False, null=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.FileField(upload_to="storage")

