from rest_framework import serializers


class FlowRetrieveIndustriesFlow(serializers.Serializer):

    class Meta:
        fields = ('sequence_number', 'name', 'name_ara',
                  'categories', 'multiple_industries_ind')
