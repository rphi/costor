from django.contrib import admin
from .models import UploadSession, UploadPackage, DbFile


# Register your models here.

@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(UploadPackage)
class UploadPackageAdmin(admin.ModelAdmin):
    pass


@admin.register(DbFile)
class FileAdmin(admin.ModelAdmin):
    pass
