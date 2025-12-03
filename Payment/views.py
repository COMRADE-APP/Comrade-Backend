from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from Payment.models import PaymentProfile, PaymentItem, PaymentLog, PaymentSlot, PaymentGroups
from Payment.serializers import PaymentProfileSerializer, PaymentItemSerializer, PaymentLogSerializer, PaymentSlotSerializer, PaymentGroupsSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination




# Create your views here.
class PaymentProfileViewSet(ModelViewSet):
    queryset = PaymentProfile.objects.all()
    serializer_class = PaymentProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'user'
    search_fields = ['user', 'payment_token', 'payment_number']
    filterset_fields = ['user', 'payment_token', 'payment_number']

    # TODO : Create a payment api trigger
    # @action(detail=True, methods=['post'])
    # def create_payment_profile(self, request):
    #     serializer = 

class PaymentItemViewSet(ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    pagination_class = PageNumberPagination
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'id'
    search_fields = ['name', 'cost', 'created_at']
    filterset_fields = ['name', 'cost', 'created_at']

    # TODO: Item creator

class PaymentLogViewSet(ModelViewSet):
    queryset = PaymentLog.objects.all()
    serializer_class = PaymentLogSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'payment_profile'
    search_fields = ['recipient', 'payment_profile', 'payment_type']
    filterset_fields = ['recipient', 'payment_profile', 'payment_type']

    # TODO: Log should be connected to payments api

class PaymentSlotViewSet(ModelViewSet):
    queryset = PaymentSlot.objects.all()
    serializer_class = PaymentSlotSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'payment_profile'
    search_fields = ['payment_profile', 'payment_group', 'created_at', 'amount']
    filterset_fields = ['payment_profile', 'payment_group', 'created_at', 'amount']

    # TODO: Should obey the maximum capacity quota

class PaymentGroupsViewSet(ModelViewSet):
    queryset = PaymentGroups.objects.all()
    serializer_class = PaymentGroupsSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    lookup_field = 'id'
    search_fields = ['max_capacity', 'payment_profile', 'item_grouping']
    filterset_fields = ['max_capacity', 'payment_profile', 'item_grouping']

    # TODO: Should be created automatically with a default of 3 people


