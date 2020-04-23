from django.contrib import admin
from .models import UploadSession, DbFile, BackupSnapshot, Object


# Register your models here.

@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(DbFile)
class FileAdmin(admin.ModelAdmin):
    pass

@admin.register(BackupSnapshot)
class SnapshotAdmin(admin.ModelAdmin):
    pass

@admin.register(Object)
class ObjectAdmin(admin.ModelAdmin):
    pass
