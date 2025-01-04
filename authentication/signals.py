# from django.contrib.auth.models import Group
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import CustomUser
#
#
#
# @receiver(post_save, sender=CustomUser)
# def add_user_type_group(sender, instance, created, **kwargs):
#     """
#     Automatically adds the group associated with
#     the user's user_type to the user's groups
#     after saving the CustomUser instance.
#     This will only trigger for newly created users.
#     """
#     if created:  # Only run when the user is created
#         if instance.user_type and instance.user_type.group:
#             user_type_group = instance.user_type.group
#             if not instance.groups.filter(id=user_type_group.id).exists():
#                 instance.groups.add(user_type_group)
#                 instance.save()  # Save the instance after adding the group
