from django.contrib.auth.models import Group
from rest_framework import serializers

from conditional_approval.models import Action, ApprovalStep, ParallelApprovalGroup, APICallCondition, \
    ApprovalStepCondition, ActionStep
from lookup.models import Lookup


class ActionBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'name', 'name_ara', 'code', 'active_ind']



class LookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lookup
        fields = ['id', 'name', 'code', 'name_ara']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class ActionSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    services = LookupSerializer(many=True, read_only=True)

    class Meta:
        model = Action
        fields = '__all__'


class ActionStepSerializer(serializers.ModelSerializer):
    action = ActionSerializer(read_only=True)
    to_status = LookupSerializer(read_only=True)
    sub_status = LookupSerializer(read_only=True)

    class Meta:
        model = ActionStep
        fields = '__all__'


class ApprovalStepConditionSerializer(serializers.ModelSerializer):
    to_status = LookupSerializer(read_only=True)
    sub_status = LookupSerializer(read_only=True)

    class Meta:
        model = ApprovalStepCondition
        fields = '__all__'


class APICallConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = APICallCondition
        fields = '__all__'


class ParallelApprovalGroupSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)

    class Meta:
        model = ParallelApprovalGroup
        fields = '__all__'


class ApprovalStepSerializer(serializers.ModelSerializer):
    service_type = LookupSerializer(read_only=True)
    status = LookupSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    priority_approver_groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalStep
        fields = '__all__'



# Master Serializer for Nested Operations
class FullApprovalStepSerializer(serializers.ModelSerializer):
    actions = ActionStepSerializer(many=True, required=False)  # ✅ optional
    parallel_approval_groups = ParallelApprovalGroupSerializer(many=True, required=False)  # ✅ optional
    approvalstepcondition_set = ApprovalStepConditionSerializer(many=True, required=False)  # ✅ optional
    apicallcondition_set = APICallConditionSerializer(many=True, required=False)  # ✅ optional
    priority_approver_groups = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalStep
        fields = [
            'id', 'service_type', 'seq', 'step_type', 'status', 'group',
            'required_approvals', 'priority_approver_groups', 'active_ind',
            'actions', 'parallel_approval_groups',
            'approvalstepcondition_set', 'apicallcondition_set'
        ]

    def get_priority_approver_groups(self, obj):
        return [{"id": g.id, "name": g.name} for g in obj.priority_approver_groups.all()]

    def create(self, validated_data):
        actions_data = validated_data.pop('actions', [])
        groups_data = validated_data.pop('parallel_approval_groups', [])
        conditions_data = validated_data.pop('approvalstepcondition_set', [])
        api_conditions_data = validated_data.pop('apicallcondition_set', [])

        step = ApprovalStep.objects.create(**validated_data)

        for item in actions_data:
            ActionStep.objects.create(approval_step=step, **item)
        for item in groups_data:
            ParallelApprovalGroup.objects.create(approval_step=step, **item)
        for item in conditions_data:
            ApprovalStepCondition.objects.create(approval_step=step, **item)
        for item in api_conditions_data:
            APICallCondition.objects.create(approval_step=step, **item)

        return step


    def update(self, instance, validated_data):
        # full nested update logic can be extended here
        return super().update(instance, validated_data)