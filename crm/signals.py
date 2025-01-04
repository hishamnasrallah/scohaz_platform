from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from crm.models import Customer, Lead, Activity, Product, Invoice

@receiver(pre_save, sender=Customer)
def pre_save_customer(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for Customer: {instance}')

@receiver(post_save, sender=Customer)
def post_save_customer(sender, instance, created, **kwargs):
    if created:
        print(f'Customer instance created: {instance}')
    else:
        print(f'Customer instance updated: {instance}')

@receiver(pre_save, sender=Lead)
def pre_save_lead(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for Lead: {instance}')

@receiver(post_save, sender=Lead)
def post_save_lead(sender, instance, created, **kwargs):
    if created:
        print(f'Lead instance created: {instance}')
    else:
        print(f'Lead instance updated: {instance}')

@receiver(pre_save, sender=Activity)
def pre_save_activity(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for Activity: {instance}')

@receiver(post_save, sender=Activity)
def post_save_activity(sender, instance, created, **kwargs):
    if created:
        print(f'Activity instance created: {instance}')
    else:
        print(f'Activity instance updated: {instance}')

@receiver(pre_save, sender=Product)
def pre_save_product(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for Product: {instance}')

@receiver(post_save, sender=Product)
def post_save_product(sender, instance, created, **kwargs):
    if created:
        print(f'Product instance created: {instance}')
    else:
        print(f'Product instance updated: {instance}')

@receiver(pre_save, sender=Invoice)
def pre_save_invoice(sender, instance, **kwargs):
    # Add custom pre-save logic here
    print(f'Pre-save hook triggered for Invoice: {instance}')

@receiver(post_save, sender=Invoice)
def post_save_invoice(sender, instance, created, **kwargs):
    if created:
        print(f'Invoice instance created: {instance}')
    else:
        print(f'Invoice instance updated: {instance}')

