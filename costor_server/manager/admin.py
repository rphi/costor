from django.contrib import admin
from .models import Agent


# Register your models here.

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    pass
