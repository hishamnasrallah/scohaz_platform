from django.db import models
from django.utils import timezone
from datetime import timedelta
from authentication.models import CustomUser


# Create your models here.
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    features = models.TextField(
        help_text="Comma-separated list of features included in the plan.")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(
        max_length=10,
        choices=(('monthly', 'Monthly'), ('annually', 'Annually')))
    max_users = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Client(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    project_id = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    contact_email = models.EmailField()

    def __str__(self):
        return self.company_name


class Subscription(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=(('active', 'Active'), ('cancelled', 'Cancelled'))
    )
    # Track the number of active projects or users allowed
    max_projects = models.PositiveIntegerField(default=0)  # Max number of projects the developer can create
    active_project_count = models.PositiveIntegerField(default=0)  # Number of active projects the developer currently has
    developers = models.ManyToManyField(CustomUser)
    auto_renew = models.BooleanField(default=True)  # New field for auto-renewal



    def save(self, *args, **kwargs):
            if not self.end_date:
                self.end_date = self.start_date + timedelta(
                    days=30 if self.plan.billing_cycle == 'monthly' else 365
                )
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.client} - {self.plan.name}"

    def is_user_limit_reached(self):
        """
        Check if the developer has reached the maximum number of allowed projects.
        """
        return self.active_project_count >= self.max_projects

    def has_active_subscription(self):
        """
        Check if the subscription is active and has not expired.
        """
        return self.status == 'active' and self.end_date > timezone.now()

    def renew(self):
        """
        Renew the subscription by extending the end_date.
        """
        if self.plan.billing_cycle == 'monthly':
            self.end_date += timedelta(days=30)
        elif self.plan.billing_cycle == 'annually':
            self.end_date += timedelta(days=365)
        self.save()

class License(models.Model):
    # project_id = models.CharField(max_length=100)  # This is the unique project identifier
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    license_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=(('active', 'Active'), ('inactive', 'Inactive'))
    )
    valid_until = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)  # New field for auto-renewal

    def __str__(self):
            return f"License for {self.client.project_id} ({self.status})"

    def renew(self):
        """
        Renew the license by extending the valid_until date.
        """
        self.valid_until += timedelta(days=30)  # Assuming monthly license
        self.save()

    def is_valid(self):
        """
        Check if the license is active and has not expired.
        """
        return self.status == 'active' and self.valid_until > timezone.now()

    def has_valid_license_for_project(self, project_id):
        """
        Check if this license is valid for the given project.
        """
        return self.client.project_id == project_id and self.is_valid()

    def get_remaining_time(self):
        """
        Return the remaining time for the license to expire.
        """
        remaining_time = self.valid_until - timezone.now()
        return remaining_time if remaining_time > timedelta(0) else timedelta(0)
