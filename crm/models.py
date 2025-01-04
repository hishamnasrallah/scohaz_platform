from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from .mixins import DynamicValidationMixin


class IntegrationConfig(models.Model):
    name = models.CharField(max_length=255)
    base_url = models.URLField()
    method = models.CharField(
        max_length=10,
        choices=[
            ('GET', 'GET'),
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('DELETE', 'DELETE')
        ]
    )
    headers = models.JSONField(blank=True, null=True)
    body = models.JSONField(blank=True, null=True)
    timeout = models.IntegerField(default=30)

    class Meta:
        verbose_name = 'Integration Config'
        verbose_name_plural = 'Integration Configs'

    def __str__(self):
        return self.name



class ValidationRule(models.Model):
    model_name = models.CharField(max_length=255)
    field_name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=50, choices=[('regex', 'Regex'), ('custom', 'Custom')])
    rule_value = models.TextField()
    error_message = models.TextField()
    user_roles = models.JSONField(blank=True, null=True)
    global_rule = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.model_name}.{self.field_name}: {self.rule_type}"
class Customer(DynamicValidationMixin, models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-created_at']

class Lead(DynamicValidationMixin, models.Model):
    title = models.CharField(max_length=255)
    STATUS_CHOICES = [['new', 'New'], ['contacted', 'Contacted'], ['qualified', 'Qualified']]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    PRIORITY_CHOICES = [['low', 'Low'], ['medium', 'Medium'], ['high', 'High']]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    customer = models.ForeignKey(
        to='crm.Customer',
        on_delete=models.CASCADE, related_name='lead_customer_set'
    )
    assigned_to = models.ForeignKey(
        to='authentication.CustomUser',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='lead_assigned_to_set'
    )
    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-created_at']

class Activity(DynamicValidationMixin, models.Model):
    ACTIVITY_TYPE_CHOICES = [['call', 'Call'], ['meeting', 'Meeting'], ['email', 'Email'], ['task', 'Task']]
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    lead = models.ForeignKey(
        to='crm.Lead',
        on_delete=models.CASCADE, related_name='activity_lead_set'
    )
    assigned_to = models.ForeignKey(
        to='authentication.CustomUser',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_assigned_to_set'
    )
    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        ordering = ['-timestamp']

class Product(DynamicValidationMixin, models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']

class Invoice(DynamicValidationMixin, models.Model):
    invoice_number = models.CharField(max_length=50, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    STATUS_CHOICES = [['draft', 'Draft'], ['issued', 'Issued'], ['paid', 'Paid'], ['cancelled', 'Cancelled']]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    customer = models.ForeignKey(
        to='crm.Customer',
        on_delete=models.CASCADE, related_name='invoice_customer_set'
    )
    created_by = models.ForeignKey(
        to='authentication.CustomUser',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_created_by_set'
    )
    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        ordering = ['-issue_date']

class Payment(DynamicValidationMixin, models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    invoice = models.ForeignKey(
        to='crm.Invoice',
        on_delete=models.CASCADE, related_name='payment_invoice_set'
    )
    received_by = models.ForeignKey(
        to='authentication.CustomUser',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_received_by_set'
    )
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-payment_date']


@receiver(post_save, sender=IntegrationConfig)
def handle_integration_post_save(sender, instance, created, **kwargs):
    if created:
        print(f"IntegrationConfig created: {instance.name}")
    else:
        print(f"IntegrationConfig updated: {instance.name}")


