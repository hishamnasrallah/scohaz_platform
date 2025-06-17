from django_filters import rest_framework as filters, BooleanFilter
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from lookup.apis.serializers import GenericLookupsSerializer
from lookup.models import Lookup


class LookupFilter(filters.FilterSet):
    parent_lookup = filters.NumberFilter(field_name='parent_lookup__id',
                                         lookup_expr='exact', required=False)
    type = filters.NumberFilter(field_name='type', lookup_expr='exact', required=False)
    name = filters.CharFilter(field_name='parent_lookup__name', lookup_expr='exact', required=False)
    id = filters.NumberFilter(field_name='id', lookup_expr='exact', required=False)
    # active_ind = BooleanFilter(field_name='active_ind', lookup_expr='exact', required=False)
    class Meta:
        model = Lookup
        fields = ['parent_lookup', 'type', 'name', 'id', 'active_ind']


class RetrieveLookupsListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = Lookup.objects.filter(active_ind=True)
    serializer_class = GenericLookupsSerializer
    filter_backends = (filters.DjangoFilterBackend,)  # Enable filtering
    filterset_class = LookupFilter  # Use the LookupFilter for this view


class LookupViewSet(viewsets.ModelViewSet):
    """
    CRUD API ViewSet for Lookup model with extra actions.
    """
    queryset = Lookup.objects.all()
    serializer_class = GenericLookupsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Optional filtering by parent or type or category.
        """
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get("parent")
        lookup_type = self.request.query_params.get("type")
        is_category = self.request.query_params.get("is_category")

        if parent_id:
            queryset = queryset.filter(parent_lookup_id=parent_id)
        if lookup_type:
            queryset = queryset.filter(type=lookup_type)
        if is_category is not None:
            queryset = queryset.filter(is_category=(is_category.lower() == "true"))

        return queryset

    @action(detail=False, methods=["get"], url_path="parents")
    def get_parent_lookups(self, request):
        """
        Extra endpoint to return only parent lookups (type == 1).
        """
        parent_lookups = Lookup.objects.filter(type=Lookup.LookupTypeChoices.LOOKUP)
        serializer = self.get_serializer(parent_lookups, many=True)
        return Response(serializer.data)