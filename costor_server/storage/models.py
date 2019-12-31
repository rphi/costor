import uuid
import hashlib
import os

from django.db import models
from manager.models import Agent


# Create your models here.

class DbFile(models.Model):
    id = models.CharField(primary_key=True, max_length=32, blank=False, null=False)  # ID is file hash
    timestamp = models.DateTimeField(auto_now_add=True)
    data = models.FileField(upload_to="storage", max_length=255, null=True, blank=True)
    valid = models.BooleanField(default=False)
    # valid set to true once file upload is complete, for status see the uploadsession


class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    expectedparts = models.IntegerField()
    receivedparts = models.IntegerField(default=0)
    fullhash = models.CharField(max_length=64, blank=False, null=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1, default="N")
    target = models.ForeignKey(DbFile, on_delete=models.SET_NULL, related_name="session", null=True, blank=True)
    # status can be "N": new, "U": uploading, "W": writing, "F": failed, "V": verfifying, "C": complete

    def save(self, *args, **kwargs):
        if not self.target and not self.id:
            # This is a new session, we need to create a file for it
            file = DbFile(id=self.fullhash)
            file.save()
            self.target = file
        super(UploadSession, self).save(*args, **kwargs)

    def append(self, data, datahash: str, sequenceno: int):
        if self.status is "N":
            # first package hitting this session, marking as uploading
            self.status = "U"
        if self.status is not "U":
            raise Exception("This session is not expecting file parts, status is %s" % self.status)

        nextpart = self.receivedparts + 1
        if sequenceno != nextpart:
            raise Exception("Received file part out of order, expecting part %i of %i, got part %i" %
                            (nextpart, self.expectedparts, sequenceno))
        if sequenceno > self.expectedparts:
            raise Exception("Unexpected file part, received part %i, only expecting %i" %
                            (sequenceno, self.expectedparts))

        sha1 = hashlib.sha1()
        for chunk in data.chunks():
            sha1.update(chunk)
        shahash = sha1.hexdigest()
        if shahash != datahash:
            raise Exception("File data doesn't match hash provided. Rejecting part.")

        self.status = "W"  # set DB object to writing mode, prevent another request appending at same time

        with self.target.data.open(mode=os.O_APPEND | os.O_EXLOCK) as file:
            for chunk in data.chunks():
                file.write(chunk)

        self.receivedparts += 1

        if self.receivedparts == self.expectedparts:
            # completed the file, time to verify and close session
            self.status = "V"

            sha1 = hashlib.sha1()
            with self.target.data.open(mode=os.O_RDONLY) as file:
                for chunk in file.chunks():
                    sha1.update(chunk)
            shahash = sha1.hexdigest()

            if shahash is not self.fullhash:
                self.status = "F"
                # self.target.delete()
                raise Exception("Mismatched hash when verifying file. PANIC")

            self.status = "C"


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


class Object(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    objhash = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=4096)
    type = models.CharField(max_length=4)
    stat = models.CharField(max_length=255)
    prime = models.ForeignKey(DbFile, on_delete=models.CASCADE, null=True, blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name="children")
    snapshot = models.ForeignKey(Snapshot, related_name="objects", on_delete=models.CASCADE, null=True)
