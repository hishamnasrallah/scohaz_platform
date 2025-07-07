# reporting_templates/services/data_service.py

import importlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal

from django.db import connection
from django.db.models import Q, QuerySet, Model
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django.template import Context, Template

from ..models import (
    PDFTemplate, PDFTemplateParameter,
    PDFTemplateDataSource, PDFGenerationLog
)

User = get_user_model()


class DataFetchingService:
    """
    Service to handle all data fetching for PDF templates
    """

    def __init__(self, template: PDFTemplate, user: User, parameters: Dict[str, Any] = None):
        self.template = template
        self.user = user
        self.parameters = parameters or {}
        self.context_data = {
            'user': user,
            'current_date': timezone.now().date(),
            'current_datetime': timezone.now(),
            'parameters': self.parameters,
        }
        self.errors = []

    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Fetch all data required for the template
        """
        try:
            # Validate parameters
            self._validate_parameters()

            # Fetch main data
            main_data = self._fetch_main_data()
            if main_data is not None:
                self.context_data['main'] = main_data

            # Fetch additional data sources
            for data_source in self.template.data_sources.filter(active_ind=True):
                source_data = self._fetch_data_source(data_source)
                if source_data is not None:
                    self.context_data[data_source.source_key] = source_data

            # Apply post-processing
            self._post_process_data()

            return self.context_data

        except Exception as e:
            self.errors.append(str(e))
            raise

    def _validate_parameters(self):
        """
        Validate provided parameters against template requirements
        """
        template_params = self.template.parameters.filter(active_ind=True)

        for param in template_params:
            param_value = self.parameters.get(param.parameter_key)

            # Check required parameters
            if param.is_required and param_value is None:
                if param.default_value:
                    self.parameters[param.parameter_key] = param.default_value
                else:
                    raise ValueError(f"Required parameter '{param.parameter_key}' is missing")

            # Type validation
            if param_value is not None:
                param_value = self._validate_parameter_type(param_value, param)
                self.parameters[param.parameter_key] = param_value

            # Additional validation rules
            if param.validation_rules:
                self._apply_validation_rules(param_value, param.validation_rules, param.parameter_key)

    def _validate_parameter_type(self, value: Any, param: PDFTemplateParameter) -> Any:
        """
        Validate and convert parameter type
        """
        try:
            if param.parameter_type == 'integer':
                return int(value)
            elif param.parameter_type == 'float':
                return float(value)
            elif param.parameter_type == 'boolean':
                return str(value).lower() in ('true', '1', 'yes')
            elif param.parameter_type == 'date':
                if isinstance(value, str):
                    return datetime.strptime(value, '%Y-%m-%d').date()
                return value
            elif param.parameter_type == 'datetime':
                if isinstance(value, str):
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                return value
            elif param.parameter_type == 'model_id':
                return int(value)
            return value
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for parameter '{param.parameter_key}': {e}")

    def _apply_validation_rules(self, value: Any, rules: Dict[str, Any], param_key: str):
        """
        Apply custom validation rules
        """
        if 'min' in rules and value < rules['min']:
            raise ValueError(f"Parameter '{param_key}' must be >= {rules['min']}")

        if 'max' in rules and value > rules['max']:
            raise ValueError(f"Parameter '{param_key}' must be <= {rules['max']}")

        if 'pattern' in rules:
            import re
            if not re.match(rules['pattern'], str(value)):
                raise ValueError(f"Parameter '{param_key}' does not match required pattern")

        if 'choices' in rules and value not in rules['choices']:
            raise ValueError(f"Parameter '{param_key}' must be one of: {rules['choices']}")

    def _fetch_main_data(self) -> Optional[Any]:
        """
        Fetch main data based on template configuration
        """
        if self.template.data_source_type == 'model':
            return self._fetch_model_data()
        elif self.template.data_source_type == 'raw_sql':
            return self._fetch_raw_sql_data()
        elif self.template.data_source_type == 'custom_function':
            return self._fetch_custom_function_data()
        return None

    def _fetch_model_data(self) -> Optional[Union[Model, QuerySet]]:
        """
        Fetch data using Django ORM
        """
        if not self.template.content_type:
            return None

        model_class = self.template.content_type.model_class()
        if not model_class:
            return None

        # Build query
        queryset = model_class.objects.all()

        # Apply default filters
        if self.template.query_filter:
            filter_dict = self._process_filter_dict(self.template.query_filter)
            queryset = queryset.filter(**filter_dict)

        # Apply parameter filters
        for param in self.template.parameters.filter(active_ind=True):
            if param.parameter_key in self.parameters:
                filter_key = f"{param.query_field}__{param.query_operator}"
                queryset = queryset.filter(**{filter_key: self.parameters[param.parameter_key]})

        # Handle self/other access
        if self.template.allow_self_generation and not self.template.allow_other_generation:
            # Filter to current user
            user_fields = self._get_user_fields(model_class)
            if user_fields:
                queryset = queryset.filter(**{user_fields[0]: self.user})

        # Apply related models
        if self.template.related_models:
            for relation in self.template.related_models.get('select_related', []):
                queryset = queryset.select_related(relation)
            for relation in self.template.related_models.get('prefetch_related', []):
                queryset = queryset.prefetch_related(relation)

        # Return single object or queryset
        if 'pk' in self.parameters or 'id' in self.parameters:
            pk = self.parameters.get('pk') or self.parameters.get('id')
            return queryset.filter(pk=pk).first()

        return queryset

    def _fetch_raw_sql_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch data using raw SQL
        """
        if not self.template.raw_sql_query:
            return None

        # Process SQL with parameters
        sql = self.template.raw_sql_query
        params = []

        # Replace parameter placeholders
        for param_key, param_value in self.parameters.items():
            placeholder = f"${{{param_key}}}"
            if placeholder in sql:
                sql = sql.replace(placeholder, '%s')
                params.append(param_value)

        # Execute query
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

        return results

    def _fetch_custom_function_data(self) -> Optional[Any]:
        """
        Fetch data using custom function
        """
        if not self.template.custom_function_path:
            return None

        try:
            # Import custom function
            module_path, func_name = self.template.custom_function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            # Call function with context
            return func(
                user=self.user,
                parameters=self.parameters,
                template=self.template
            )
        except Exception as e:
            raise ValueError(f"Error calling custom function: {e}")

    def _fetch_data_source(self, data_source: PDFTemplateDataSource) -> Optional[Any]:
        """
        Fetch data from additional data source
        """
        # Check cache first
        if data_source.cache_timeout > 0:
            cache_key = self._get_cache_key(data_source)
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        # Fetch based on method
        if data_source.fetch_method == 'model_query':
            data = self._fetch_data_source_model(data_source)
        elif data_source.fetch_method == 'raw_sql':
            data = self._fetch_data_source_sql(data_source)
        elif data_source.fetch_method == 'custom_function':
            data = self._fetch_data_source_function(data_source)
        elif data_source.fetch_method == 'related_field':
            data = self._fetch_data_source_related(data_source)
        else:
            data = None

        # Apply post-processing
        if data is not None and data_source.post_process_function:
            data = self._apply_post_process(data, data_source.post_process_function)

        # Cache if configured
        if data is not None and data_source.cache_timeout > 0:
            cache.set(cache_key, data, data_source.cache_timeout)

        return data

    def _fetch_data_source_model(self, data_source: PDFTemplateDataSource) -> Optional[QuerySet]:
        """
        Fetch model-based data source
        """
        if not data_source.content_type:
            return None

        model_class = data_source.content_type.model_class()
        if not model_class:
            return None

        queryset = model_class.objects.all()

        # Apply filters
        if data_source.filter_config:
            filter_dict = self._process_filter_dict(data_source.filter_config)
            queryset = queryset.filter(**filter_dict)

        return queryset

    def _fetch_data_source_sql(self, data_source: PDFTemplateDataSource) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch SQL-based data source
        """
        if not data_source.raw_sql:
            return None

        sql = data_source.raw_sql
        params = []

        # Process parameters
        for param_key, param_value in self.parameters.items():
            placeholder = f"${{{param_key}}}"
            if placeholder in sql:
                sql = sql.replace(placeholder, '%s')
                params.append(param_value)

        # Also process context variables
        for key, value in self.context_data.items():
            if isinstance(value, (str, int, float, bool, date, datetime)):
                placeholder = f"${{{key}}}"
                if placeholder in sql:
                    sql = sql.replace(placeholder, '%s')
                    params.append(value)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

        return results

    def _fetch_data_source_function(self, data_source: PDFTemplateDataSource) -> Optional[Any]:
        """
        Fetch function-based data source
        """
        if not data_source.custom_function_path:
            return None

        try:
            module_path, func_name = data_source.custom_function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            return func(
                user=self.user,
                parameters=self.parameters,
                context=self.context_data,
                data_source=data_source
            )
        except Exception as e:
            raise ValueError(f"Error calling data source function: {e}")

    def _fetch_data_source_related(self, data_source: PDFTemplateDataSource) -> Optional[Any]:
        """
        Fetch related field data
        """
        if not data_source.query_path or 'main' not in self.context_data:
            return None

        # Navigate through the path
        obj = self.context_data['main']
        for part in data_source.query_path.split('__'):
            if hasattr(obj, part):
                obj = getattr(obj, part)
                if callable(obj):
                    obj = obj()
            else:
                return None

        return obj

    def _process_filter_dict(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process filter dictionary, replacing variables with actual values
        """
        processed = {}

        for key, value in filter_dict.items():
            # Handle template variables
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                var_name = value[2:-2].strip()

                # Check parameters
                if var_name in self.parameters:
                    value = self.parameters[var_name]
                # Check context
                elif '.' in var_name:
                    value = self._get_nested_value(self.context_data, var_name)
                elif var_name == 'current_user':
                    value = self.user
                elif var_name == 'current_date':
                    value = timezone.now().date()

            processed[key] = value

        return processed

    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """
        Get nested value from dictionary using dot notation
        """
        parts = path.split('.')
        value = obj

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value

    def _apply_post_process(self, data: Any, function_path: str) -> Any:
        """
        Apply post-processing function to data
        """
        try:
            module_path, func_name = function_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            return func(data, context=self.context_data)
        except Exception as e:
            print(f"Error in post-processing: {e}")
            return data

    def _post_process_data(self):
        """
        Apply final post-processing to all context data
        """
        # Process template variables
        for var in self.template.variables.all():
            try:
                # Get value from data source
                value = self._get_nested_value(self.context_data, var.data_source)

                # Apply transformation
                if value is not None and var.transform_function:
                    value = self._apply_post_process(value, var.transform_function)

                # Apply formatting
                if value is not None and var.format_string:
                    if isinstance(value, (date, datetime)):
                        value = value.strftime(var.format_string)
                    elif isinstance(value, (int, float, Decimal)):
                        value = var.format_string.format(value)

                # Use default if needed
                if value is None and var.default_value:
                    value = var.default_value

                # Set in context
                self.context_data[var.variable_key] = value

            except Exception as e:
                print(f"Error processing variable {var.variable_key}: {e}")
                if var.is_required:
                    raise

    def _get_user_fields(self, model_class: type) -> List[str]:
        """
        Get fields that reference User model
        """
        user_fields = []

        for field in model_class._meta.fields:
            if field.related_model == User:
                user_fields.append(field.name)

        return user_fields

    def _get_cache_key(self, data_source: PDFTemplateDataSource) -> str:
        """
        Generate cache key for data source
        """
        param_str = '_'.join(f"{k}:{v}" for k, v in sorted(self.parameters.items()))
        return f"pdf_data_{self.template.id}_{data_source.id}_{self.user.id}_{param_str}"


class TemplateQueryBuilder:
    """
    Build queries for template data fetching
    """

    @staticmethod
    def build_query_from_params(
            model_class: type,
            parameters: List[PDFTemplateParameter],
            param_values: Dict[str, Any]
    ) -> Q:
        """
        Build Q object from parameters
        """
        query = Q()

        for param in parameters:
            if param.parameter_key in param_values:
                value = param_values[param.parameter_key]
                if value is not None:
                    field_lookup = f"{param.query_field}__{param.query_operator}"
                    query &= Q(**{field_lookup: value})

        return query

    @staticmethod
    def apply_security_filters(
            queryset: QuerySet,
            user: User,
            template: PDFTemplate
    ) -> QuerySet:
        """
        Apply security filters based on template configuration
        """
        model_class = queryset.model

        # If only self-generation allowed
        if template.allow_self_generation and not template.allow_other_generation:
            # Find user reference fields
            user_fields = []
            for field in model_class._meta.fields:
                if field.related_model == User:
                    user_fields.append(field.name)

            # Apply filter
            if user_fields:
                user_query = Q()
                for field in user_fields:
                    user_query |= Q(**{field: user})
                queryset = queryset.filter(user_query)

        return queryset