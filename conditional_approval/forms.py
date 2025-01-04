from conditional_approval.models import ApprovalStep
from django import forms
import os


class ApprovalStepForm(forms.ModelForm):
    class Meta:
        model = ApprovalStep
        fields = '__all__'  # Include all fields or specify them

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide the buttons for foreign key fields

        # Add your foreign key fields here
        for field in ['case_type', 'role', 'action', 'next_step']:
            self.fields[field].widget.can_add_related = False
            self.fields[field].widget.can_change_related = False
            self.fields[field].widget.can_delete_related = False
            # self.fields[field].widget.can_view_related = False

# Path to your directory containing the Python files (adjust as necessary)
# MODULE_DIRECTORY = os.path.join(os.path.dirname(__file__),
# 'injection_approval_flow_functions')

# "utils"  # Adjust to your directory path


utils_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
target_folder = os.path.join(utils_dir, 'utils/injection_approval_flow_functions')
