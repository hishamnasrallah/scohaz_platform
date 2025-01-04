from django.contrib import admin
from lookup.models import Lookup, LookupConfig

# Register your models here.


class ParentLookupFilter(admin.SimpleListFilter):
    title = 'Parent Lookup'  # The title of the filter in the admin interface
    parameter_name = 'parent_lookup'  # The query parameter for filtering

    def lookups(self, request, model_admin):
        # Get all unique parent lookups (ignoring null)
        parents = Lookup.objects.filter(
            parent_lookup__isnull=False).values_list(
            'parent_lookup__name', flat=True).distinct()
        return [(parent, parent) for parent in parents]

    def queryset(self, request, queryset):
        if self.value():
            # We are filtering by parent_lookup's name,
            # so we perform a lookup on the 'parent_lookup'
            return queryset.filter(parent_lookup__name=self.value())
        return queryset


class LookupChildrenInline(admin.TabularInline):
    model = Lookup
    extra = 1
    fk_name = 'parent_lookup'


@admin.register(Lookup)
class LookupAdmin(admin.ModelAdmin):
    list_display = ['parent_lookup', 'type', 'name', 'name_ara', 'code', 'active_ind']
    ordering = ('parent_lookup', 'name')
    list_filter = ('type', 'active_ind', ParentLookupFilter)
    inlines = [LookupChildrenInline]
    search_fields = ('name', 'parent_lookup__name')
    # autocomplete_fields = ['parent_lookup']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent_lookup":
            kwargs["queryset"] = Lookup.objects.filter(
                parent_lookup__isnull=True)  # Only show records with no parent
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(LookupConfig)
class LookupConfigAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'field_name', 'lookup_category')
    list_filter = ('model_name', 'field_name')
    search_fields = ('model_name', 'field_name', 'lookup_category')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Get dynamic model choices
        model_choices = LookupConfig.get_model_choices()
        field_choices = []

        if obj:
            # If a LookupConfig object exists, get
            # field choices based on the selected model
            field_choices = LookupConfig.get_model_choices()

        form.base_fields['model_name'].choices \
            = model_choices
        form.base_fields['lookup_category'].choices \
            = LookupConfig.get_lookup_category_choices()
        form.base_fields['field_name'].choices \
            = field_choices

        return form
