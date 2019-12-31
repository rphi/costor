from django.contrib import admin
from .models import UploadSession, DbFile


# Register your models here.

@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(DbFile)
class FileAdmin(admin.ModelAdmin):
    pass
