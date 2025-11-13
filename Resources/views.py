from django.shortcuts import render
from Resources.serializers import ResourceSerializer
from Resources.models import Resource
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.status import HTTP_201_CREATED, HTTP_202_ACCEPTED, HTTP_200_OK, HTTP_400_BAD_REQUEST

# Create your views here.
class ResourceViewSet(ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
