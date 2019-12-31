from django.db import models
from django.contrib.auth.models import User
import uuid


# Create your models here.

class Agent(models.Model):
    name = models.CharField(primary_key=True, max_length=30)
    comment = models.TextField(max_length=120)
    users = models.ManyToManyField(User, related_name="agents", blank=True)
