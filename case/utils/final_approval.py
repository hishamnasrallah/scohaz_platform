# Suppose somewhere in your workflow, after final approval:

from case.utils.mapper import execute_mappings

def on_case_approved(case):
    # TODO:// add the dynamic logic to validate its the final stage or approval regardless of the value of status
    # Maybe you have some logic that changes the case status
    case.status = "Approved"
    case.save()

    # Then call execute_mappings
    execute_mappings(case)
