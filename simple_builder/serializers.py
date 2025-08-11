from rest_framework import serializers
from .models import ComponentTemplate, WidgetMapping


class ComponentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComponentTemplate
        fields = '__all__'


class ComponentTemplateBuilderSerializer(serializers.ModelSerializer):
    display_order = serializers.SerializerMethodField()
    widget_group = serializers.SerializerMethodField()
    show_in_builder = serializers.SerializerMethodField()

    class Meta:
        model = ComponentTemplate
        fields = [
            'id', 'name', 'category', 'flutter_widget', 'icon',
            'description', 'default_properties', 'can_have_children',
            'max_children', 'display_order', 'widget_group', 'show_in_builder'
        ]

    def get_display_order(self, obj):
        return obj.default_properties.get('display_order', 999)

    def get_widget_group(self, obj):
        return obj.default_properties.get('widget_group', 'Other')

    def get_show_in_builder(self, obj):
        return obj.default_properties.get('show_in_builder', True)


class OrganizedComponentsSerializer(serializers.Serializer):
    def to_representation(self, components_dict):
        result = {}
        for group_name, components in components_dict.items():
            result[group_name] = ComponentTemplateBuilderSerializer(
                components, many=True, context=self.context
            ).data
        return result


class WidgetMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetMapping
        fields = '__all__'