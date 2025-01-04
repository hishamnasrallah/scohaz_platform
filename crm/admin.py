from django.contrib import admin
from crm.models import *


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'method')
    search_fields = ('name', 'base_url')



@admin.register(ValidationRule)
class ValidationRuleAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'field_name', 'rule_type', 'error_message')
    search_fields = ('model_name', 'field_name', 'rule_type')


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone_number', 'company_name', 'address', 'is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'phone_number', 'company_name']
    list_filter = ['is_active', 'created_at']

admin.site.register(Customer, CustomerAdmin)

class LeadAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'value', 'source', 'created_at']
    search_fields = ['title', 'status', 'priority', 'source']
    list_filter = ['created_at']

admin.site.register(Lead, LeadAdmin)

class ActivityAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'description', 'timestamp', 'is_completed']
    search_fields = ['activity_type']
    list_filter = ['timestamp', 'is_completed']

admin.site.register(Activity, ActivityAdmin)

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'description', 'is_active']
    search_fields = ['name']
    list_filter = ['is_active']

admin.site.register(Product, ProductAdmin)

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'total', 'issue_date', 'due_date', 'status', 'discount']
    search_fields = ['invoice_number', 'status']
    list_filter = ['issue_date', 'due_date']

admin.site.register(Invoice, InvoiceAdmin)

class PaymentAdmin(admin.ModelAdmin):
    list_display = ['amount', 'payment_date']
    search_fields = []
    list_filter = ['payment_date']

admin.site.register(Payment, PaymentAdmin)

