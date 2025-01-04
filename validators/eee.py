from crm.models import ValidationRule  # Adjust the import path based on your app structure

# Example rules for Customer model
ValidationRule.objects.create(
    model_name="Customer",
    field_name="email",
    rule_type="regex",
    rule_value=r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)",
    error_message="The email format is invalid.",
)

ValidationRule.objects.create(
    model_name="Customer",
    field_name="phone_number",
    rule_type="custom",
    rule_value="utils.validators.validate_phone_number",
    error_message="The phone number is invalid.",
)

ValidationRule.objects.create(
    model_name="Customer",
    field_name="is_active",
    rule_type="custom",
    rule_value="utils.validators.validate_is_active_permission",
    user_role="Admin",  # Only applies to Admin users
    error_message="Only Admins can set a customer as active.",
)

# Example rules for Lead model
ValidationRule.objects.create(
    model_name="Lead",
    field_name="status",
    rule_type="regex",
    rule_value=r"^(new|contacted|qualified)$",  # Must match predefined choices
    error_message="Invalid status value.",
)

ValidationRule.objects.create(
    model_name="Lead",
    field_name="value",
    rule_type="custom",
    rule_value="crm.validators.validate_lead_value",
    error_message="Lead value must be a positive number.",
)

# Example rules for Invoice model
ValidationRule.objects.create(
    model_name="Invoice",
    field_name="discount",
    rule_type="custom",
    rule_value="crm.validators.validate_discount_range",
    error_message="Discount must be between 0 and 100%.",
)

ValidationRule.objects.create(
    model_name="Invoice",
    field_name="due_date",
    rule_type="custom",
    rule_value="crm.validators.validate_due_date",
    error_message="The due date cannot be before the issue date.",
)
