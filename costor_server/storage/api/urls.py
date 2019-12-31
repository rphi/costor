"""cores URL Configuration
The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework import routers, serializers, viewsets

from .views import upload, authcheck


router = routers.DefaultRouter()

urlpatterns = [
    path('upload/new', upload.create_session),
    path('upload/append', upload.append_to_session),
    path('upload/status', upload.get_status),
    path('upload/checkforobj', upload.check_for_object),
    path('authcheck', authcheck.auth_check),
    path('', include(router.urls))
]