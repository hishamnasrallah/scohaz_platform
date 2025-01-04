from django.contrib import admin
from license_subscription_manager.models import (License,
                                                 Subscription,
                                                 Client,
                                                 SubscriptionPlan)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'billing_cycle', 'max_users', 'created_at')
    search_fields = ('name',)
    ordering = ('created_at',)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'project_id', 'contact_email', 'user')
    search_fields = ('company_name', 'project_id', 'contact_email', 'user__username')
    ordering = ('company_name', 'project_id')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('client', 'plan', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'plan__name', 'start_date')
    search_fields = ('client__company_name', 'plan__name')
    ordering = ('-start_date',)


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('client__project_id', 'client', 'license_key', 'status', 'valid_until')
    search_fields = ('license_key', 'client__project_id', 'client__company_name')
    list_filter = ('status', 'valid_until')
    ordering = ('-valid_until',)
