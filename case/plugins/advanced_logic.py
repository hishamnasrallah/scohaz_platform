# # example of custom plugin
#
# # myapp/plugins/advanced_vacation.py
#
# from hr.models import Vacation  # Example
# from django.db.models import Q
#
# def find_records(case, mapper_target):
#     """
#     Example: find all Vacation records that overlap certain date range.
#     """
#     case_data = case.case_data
#     start = case_data["vacation"]["start_date"]
#     end = case_data["vacation"]["end_date"]
#     employee_id = case_data["vacation"]["employee_id"]
#
#     return Vacation.objects.filter(
#         employee_id=employee_id,
#         start_date__lte=end,
#         end_date__gte=start
#     )
#
# def process_records(case, mapper_target, found_objects):
#     """
#     Merge logic:
#       - If we find multiple overlapping vacations, unify them into one record
#         with earliest start and latest end.
#       - If no record found, create a new one.
#     """
#     if not found_objects.exists():
#         # Create a new
#         vac = Vacation()
#         fill_fields_from_case(vac, case)
#         vac.save()
#         return vac
#     else:
#         # Merge them
#         main_vac = found_objects.first()
#         earliest_start = min(v.start_date for v in found_objects)
#         latest_end = max(v.end_date for v in found_objects)
#         main_vac.start_date = earliest_start
#         main_vac.end_date = latest_end
#         # Possibly also update reason, etc.
#         fill_fields_from_case(main_vac, case)
#         main_vac.save()
#
#         # delete duplicates except the main
#         to_delete = found_objects.exclude(pk=main_vac.pk)
#         to_delete.delete()
#
#         return main_vac
#
# def fill_fields_from_case(vacation_obj, case):
#     # Very naive example: fill from case_data
#     data = case.case_data["vacation"]
#     vacation_obj.employee_id = data["employee_id"]
#     vacation_obj.reason = data.get("reason", "")
