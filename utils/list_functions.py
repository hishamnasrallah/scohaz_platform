import os
import importlib.util
import inspect


from time import time

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def list_functions(request):
    '''

    :param request:
    :return:

    get:
      Return a list of all existing users.

    post:
      Create a new user instance.

    '''
    # Example usage
    # "utils"  # Adjust to your directory path
    utils_dir = os.path.dirname(os.path.abspath(__file__))
    target_folder = os.path.join(utils_dir, 'injection_approval_flow_functions')

    all_functions = list_functions_in_directory(target_folder)

    # Print the functions in each file
    for module, funcs in all_functions.items():
        print(f"Functions in {module}.py:")
        for func in funcs:
            print(f"  - {func}")

    resp = f"PONG@{time()}"
    return Response(resp)


def list_functions_in_directory(directory_path):
    functions = {}

    # Loop through all files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith(".py") and filename != "__init__.py":
            file_path = os.path.join(directory_path, filename)

            # Load the Python file as a module
            module_name = filename[:-3]  # Remove '.py' extension
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get all functions in the module
            all_functions = inspect.getmembers(module, inspect.isfunction)

            # Filter out imported functions: we
            # only want functions defined in the module
            custom_functions = [
                func[0] for func in all_functions
                if func[1].__module__ == module_name
            ]  # Only include custom functions

            functions[module_name] = custom_functions

    return functions


# def list_functions_in_directory(directory_path):
#     functions = {}
#
#     # Loop through all files in the directory
#     for filename in os.listdir(directory_path):
#         if filename.endswith(".py") and filename != "__init__.py":
#             file_path = os.path.join(directory_path, filename)
#
#             # Load the Python file as a module
#             module_name = filename[:-3]  # Remove '.py' extension
#             spec = importlib.util.spec_from_file_location(module_name, file_path)
#             module = importlib.util.module_from_spec(spec)
#             spec.loader.exec_module(module)
#
#             # Get all functions in the module
#             all_functions = inspect.getmembers(module, inspect.isfunction)
#
#             # Filter out imported functions:
#             # we only want functions defined in the module
#             custom_functions = [
#                 func[0] for func in all_functions
#                 if func[1].__module__ == module_name  # Only include custom functions
#             ]
#
#             functions[module_name] = custom_functions
#
#     return functions
