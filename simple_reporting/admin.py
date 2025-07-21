# reporting_templates/admin.py

from django.contrib import admin
from django import forms
from .models import PDFTemplate, PDFElement


class PDFElementForm(forms.ModelForm):
    """Custom form for PDFElement to handle conditional field display"""
    class Meta:
        model = PDFElement
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add help text for complex fields
        self.fields['image_field_path'].help_text = (
            'Path to image field, e.g., "case_data[uploaded_files]" '
            'or "profile_image" for simple fields'
        )
        self.fields['image_additional_filters'].help_text = (
            'JSON filters, e.g., {"size": "large"} or {"category": "profile"}'
        )

    class Media:
        js = ('admin/js/pdfelement_admin.js',)


class PDFElementInline(admin.TabularInline):
    model = PDFElement
    form = PDFElementForm
    extra = 1

    fieldsets = (
        ('Basic', {
            'fields': ('element_type', 'x_position', 'y_position')
        }),
        ('Text Settings', {
            'fields': ('text_content', 'is_dynamic', 'font_size'),
            'classes': ('text-fields',)
        }),
        ('Image Settings', {
            'fields': ('image_field_path', 'image_filter_type', 'image_selection_method',
                       'image_filename_contains', 'image_additional_filters',
                       'image_width', 'image_height', 'image_maintain_aspect'),
            'classes': ('image-fields',)
        })
    )


# Alternative approach with separate inlines for better UX
class PDFTextElementInline(admin.TabularInline):
    model = PDFElement
    extra = 1
    verbose_name = "Text Element"
    verbose_name_plural = "Text Elements"

    fields = ['element_type', 'x_position', 'y_position', 'text_content',
              'is_dynamic', 'font_size']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(element_type='text')

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'element_type':
            kwargs['initial'] = 'text'
            kwargs['widget'] = forms.HiddenInput()
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class PDFImageElementInline(admin.TabularInline):
    model = PDFElement
    extra = 1
    verbose_name = "Image Element"
    verbose_name_plural = "Image Elements"

    fields = ['element_type', 'x_position', 'y_position', 'image_field_path',
              'image_filter_type', 'image_selection_method', 'image_filename_contains',
              'image_additional_filters', 'image_width', 'image_height',
              'image_maintain_aspect']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(element_type='image')

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'element_type':
            kwargs['initial'] = 'image'
            kwargs['widget'] = forms.HiddenInput()
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'image_additional_filters':
            kwargs['widget'] = forms.Textarea(attrs={'rows': 2, 'cols': 40})
        return super().formfield_for_dbfield(db_field, request, **kwargs)


@admin.register(PDFTemplate)
class PDFTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'content_type', 'page_size',
                    'page_orientation', 'background_type', 'created_at', 'active']
    list_filter = ['active', 'content_type', 'page_size', 'page_orientation', 'background_type']
    search_fields = ['name', 'code']
    readonly_fields = ['created_by', 'created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'active')
        }),
        ('Page Setup', {
            'fields': ('page_size', 'page_orientation', 'custom_width',
                       'custom_height', 'ratio_base_width'),
            'description': 'Configure page dimensions and orientation'
        }),
        ('Data Configuration', {
            'fields': ('content_type', 'query_filter')
        }),
        ('Background Settings', {
            'fields': ('background_type', 'background_color', 'background_image',
                       'background_pdf', 'background_opacity'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    # Choose one of these approaches:

    # Option 1: Single inline with all fields
    # inlines = [PDFElementInline]

    # Option 2: Separate inlines for text and image (better UX)
    inlines = [PDFTextElementInline, PDFImageElementInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Optional: Register PDFElement separately for advanced editing
@admin.register(PDFElement)
class PDFElementAdmin(admin.ModelAdmin):
    list_display = ['template', 'element_type', 'position_display',
                    'content_preview', 'image_config_preview']
    list_filter = ['template', 'element_type']
    search_fields = ['template__name', 'text_content', 'image_field_path']

    fieldsets = (
        ('Template & Type', {
            'fields': ('template', 'element_type')
        }),
        ('Position', {
            'fields': ('x_position', 'y_position'),
            'description': 'Position in points from top-left corner'
        }),
        ('Text Configuration', {
            'fields': ('text_content', 'is_dynamic', 'font_size'),
            'classes': ('collapse',),
            'description': 'Settings for text elements'
        }),
        ('Image Configuration', {
            'fields': (
                'image_field_path',
                'image_filter_type',
                'image_selection_method',
                'image_filename_contains',
                'image_additional_filters'
            ),
            'classes': ('collapse',),
            'description': 'Settings for image elements'
        }),
        ('Image Display', {
            'fields': ('image_width', 'image_height', 'image_maintain_aspect'),
            'classes': ('collapse',),
            'description': 'Image sizing and display options'
        })
    )

    def position_display(self, obj):
        return f"({obj.x_position}, {obj.y_position})"
    position_display.short_description = "Position (x, y)"

    def content_preview(self, obj):
        if obj.element_type == 'text':
            if obj.is_dynamic:
                return f"Dynamic: {obj.text_content[:50]}"
            return obj.text_content[:50] if obj.text_content else "-"
        return "-"
    content_preview.short_description = "Text Content"

    def image_config_preview(self, obj):
        if obj.element_type == 'image':
            config = f"Path: {obj.image_field_path}"
            if obj.image_filter_type:
                config += f" | Filter: {obj.image_filter_type}"
            return config
        return "-"
    image_config_preview.short_description = "Image Config"