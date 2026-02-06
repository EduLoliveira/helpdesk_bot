from rest_framework import viewsets
from app_project.api import serializers
from app_project import models

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.UsuarioSerializer
    queryset = models.Usuario.objects.all()