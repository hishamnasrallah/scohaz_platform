from rest_framework import serializers

from conditional_approval.models import Action


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'name', 'name_ara', 'code', 'active_ind']
