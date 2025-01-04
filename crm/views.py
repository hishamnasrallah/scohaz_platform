from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from crm.models import Customer, Lead, Activity, Product, Invoice, Payment, IntegrationConfig, ValidationRule
from crm.serializers import CustomerSerializer, LeadSerializer, ActivitySerializer, ProductSerializer, InvoiceSerializer, PaymentSerializer, IntegrationConfigSerializer, ValidationRuleSerializer
from crm.utils.api import make_api_call


class IntegrationConfigViewSet(viewsets.ModelViewSet):
    queryset = IntegrationConfig.objects.all()
    serializer_class = IntegrationConfigSerializer

    @action(detail=True, methods=['post'], url_path='trigger')
    def trigger_integration(self, request, pk=None):
        integration = self.get_object()
        response = make_api_call(
            base_url=integration.base_url,
            method=integration.method,
            headers=integration.headers,
            body=integration.body,
            timeout=integration.timeout,
        )
        return Response(response, status=status.HTTP_200_OK if "error" not in response else status.HTTP_400_BAD_REQUEST)

class ValidationRuleViewSet(viewsets.ModelViewSet):
    queryset = ValidationRule.objects.all()
    serializer_class = ValidationRuleSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Customer'}
        return Response(custom_data, status=status.HTTP_200_OK)

class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Lead'}
        return Response(custom_data, status=status.HTTP_200_OK)

class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Activity'}
        return Response(custom_data, status=status.HTTP_200_OK)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Product'}
        return Response(custom_data, status=status.HTTP_200_OK)

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Invoice'}
        return Response(custom_data, status=status.HTTP_200_OK)

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def list(self, request, *args, **kwargs):
        # Add conditional filtering based on query params
        queryset = self.get_queryset()
        filter_param = request.query_params.get('filter_param')
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='custom-action')
    def custom_action(self, request):
        # Add custom action logic here
        custom_data = {'message': f'Custom action triggered for Payment'}
        return Response(custom_data, status=status.HTTP_200_OK)
