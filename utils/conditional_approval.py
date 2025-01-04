import os
import importlib.util
from conditional_approval.models import ApprovalStepCondition
import ast

import re


def validate_dict_values(values, regex_patterns):
    """
    Validate the values in the first dictionary against
     the regex patterns in the second dictionary.
    Only keys present in the regex_patterns dictionary will be checked.

    Parameters:
    values (dict): The dictionary containing actual values.
    regex_patterns (dict): The dictionary containing regex patterns for each key.

    Returns:
    bool: True if all relevant values are valid
    according to the regex patterns, False otherwise.
    """
    for key, pattern in regex_patterns.items():
        value = values.get(key)
        if value is not None:  # Check only if the key exists in the values dictionary
            # Convert value to string to match against the regex
            is_valid = bool(re.match(pattern, str(value)))
            if not is_valid:
                # Return False immediately if any relevant value is invalid
                return False

    return True  # All relevant values are valid


def evaluate_conditions(case_obj, approval_step):
    """
    Evaluate conditions for an approval step and return the result.
    :param case_obj: The case instance.
    :param approval_step: The current approval step.
    :return: Tuple (result: bool, condition_obj: ApprovalStepCondition)
    """
    conditions = ApprovalStepCondition.objects.filter(
        approval_step=approval_step,
        active_ind=True
    )

    for condition in conditions:
        if condition.condition_logic:
            # Evaluate each condition in the list
            result = True
            for logic in condition.condition_logic:
                field_name = logic.get('field')
                operation = logic.get('operation')
                expected_value = logic.get('value')
                case_value = case_obj.case_data.get(field_name)

                if operation == "=":
                    result &= (case_value == expected_value)
                elif operation == "!=":
                    result &= (case_value != expected_value)
                elif operation == ">":
                    result &= (case_value > expected_value)
                elif operation == "<":
                    result &= (case_value < expected_value)
                elif operation == ">=":
                    result &= (case_value >= expected_value)
                elif operation == "<=":
                    result &= (case_value <= expected_value)
                elif operation == "contains":
                    result &= (str(expected_value) in str(case_value))
                elif operation == "startswith":
                    result &= str(case_value).startswith(str(expected_value))
                elif operation == "endswith":
                    result &= str(case_value).endswith(str(expected_value))
                elif operation == "in":
                    result &= (case_value in expected_value)
                elif operation == "not in":
                    result &= (case_value not in expected_value)
                else:
                    result = False

                if not result:
                    break  # Exit early if any condition fails

            if result:
                return True, condition

    return False, None


# import re
# import json


# def validate_value(value, regex_value):
#     """
#     Validate the value against the provided regex pattern.
#
#     Parameters:
#     value (str): The value to validate (could be email, number, name, etc.).
#     regex_value (str): The regex pattern as a string.
#
#     Returns:
#     bool: True if the value matches the regex pattern, False otherwise.
#     """
#     pattern = re.compile(regex_value)
#     return pattern.match(value) is not None

# def execute_action(case, condition):
#
#     regex = condition.condition_expression["email"]
#     for field in condition.keys():
#         print(field)
#     # is_valid = validate_email(email_to_validate, email_regex)
#
#     print("hisham")
#     # if validate_regex()
#     if condition.action_type == 'change_status':
#         case.status = condition.action_value
#         case.save()
#     elif condition.action_type == 'send_email':
#         # Implement email sending logic here
#         pass

# def evaluate_conditions(case, approval_step):
#     conditions = ApprovalStepCondition.objects.filter(approval_step=approval_step)
#
#     for condition in conditions:
#         # Safe evaluation of conditions using ast.literal_eval for safety
#         try:
#             # Prepare the context for eval
#             context = {
#                 'no_of_child': case.no_of_child,
#                 'net_profit': case.total_income - case.total_cost,
#                 'name': case.name,
#                 'email': case.email,
#                 'is_valid_email': lambda email: bool(RegexValidator()(email)),
#             }
#
#             # Evaluate the condition expression
#             if eval(condition.condition_expression, {}, context):
#                 execute_action(case, condition)
#
#         except Exception as e:
#             # Handle errors (e.g., log them)
#             print(f"Error evaluating condition in approval step condition: {e}")
#
#
# def execute_action(case, condition):
#     if condition.action_type == 'change_status':
#         case.status = condition.action_value
#         case.save()
#     elif condition.action_type == 'send_email':
#         # Implement email sending logic here
#         pass
