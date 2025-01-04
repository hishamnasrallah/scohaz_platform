from django_filters import rest_framework as filters, BooleanFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from lookup.apis.serializers import GenericLookupsSerializer
from lookup.models import Lookup


class LookupFilter(filters.FilterSet):
    parent_lookup = filters.NumberFilter(field_name='parent_lookup__id',
                                         lookup_expr='exact', required=False)
    type = filters.NumberFilter(field_name='type', lookup_expr='exact', required=False)
    id = filters.NumberFilter(field_name='id', lookup_expr='exact', required=False)
    # active_ind = BooleanFilter(field_name='active_ind', lookup_expr='exact', required=False)
    class Meta:
        model = Lookup
        fields = ['parent_lookup', 'type', 'id', 'active_ind']


class RetrieveLookupsListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = Lookup.objects.filter(active_ind=True)
    serializer_class = GenericLookupsSerializer
    filter_backends = (filters.DjangoFilterBackend,)  # Enable filtering
    filterset_class = LookupFilter  # Use the LookupFilter for this view
