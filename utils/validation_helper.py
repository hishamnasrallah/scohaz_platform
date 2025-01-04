VALIDATION_TYPE = {
    "required": "NullValidator",    # done
    "string": "StringValidator",  # done
    "alpha": "AlphaValidator",  # done
    "email": "EmailValidator",   # done
    "url": "URLValidator",      # done
    "integer": "ValidateInteger",   # done

    "max_value": "MaxValueValidator",   # done
    "min_value": "MinValueValidator",   # done

    "min_len": "MinLengthValidator",    # done
    "max_len": "MaxLengthValidator",    # done

    "extensions": "FileExtensionValidator",  # done
}

VALIDATION_TYPES_NEED_SPECIAL_PARAMS = {
    # numbers
    "max_value": "MaxValueValidator",
    "min_value": "MinValueValidator",
    # text
    "min_len": "MinLengthValidator",
    "max_len": "MaxLengthValidator",
    # file extensions
    "extensions": "FileExtensionValidator",
}

VALIDATION_TYPES_NEED_SPECIAL_LIMIT_VALUE = {
    # numbers
    "max_value": "MaxValueValidator",
    "min_value": "MinValueValidator",
    # text
    "min_len": "MinLengthValidator",
    "max_len": "MaxLengthValidator",
    # file extensions
    # "extensions": "FileExtensionValidator",
}

VALIDATION_TYPES_NEED_SPECIAL_EXTENSIONS = {
    # numbers
    # "max_value": "MaxValueValidator",
    # "min_value": "MinValueValidator",
    # text
    # "min_len": "MinLengthValidator",
    # "max_len": "MaxLengthValidator",
    # file extensions
    "extensions": "FileExtensionValidator",
}


VALIDATION_RRORS = {
    "required": "this service_flow is required service_flow",  # done
    "string": "this service_flow accept only string",  # done
    "alpha": "this service_flow accepted just alphabet characters",    # done
    "email": "please enter correct email",  # done
    "url": "please enter correct link/URL",  # done
    "integer": "please enter correct real number ",
    "max_value": "please enter number equal or less than {}",
    "min_value": "please enter number equal or greater than {}",
    "min_len": "please enter length equal or greater than {}",
    "max_len": "please enter length equal or less than {}",
    "extensions": "please choose file with extension one of the allowed extensions {}",
}
