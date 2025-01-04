

def write_in_console_case_info(case):
    try:
        print(case.serial_number)
        print(case.status)
        print(case.assigned_emp)
    except Exception as e:
        print("error writing in the console: ", e)
    return True
