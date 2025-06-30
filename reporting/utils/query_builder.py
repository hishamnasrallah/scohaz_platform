from django.db import models
from django.db.models import Q, F, Count, Sum, Avg, Min, Max, Value, Case, When
from django.db.models.functions import Coalesce, Cast, Concat
from django.core.exceptions import FieldError
from django.utils import timezone
from typing import Dict, List, Any, Optional, Union
import logging
import time
import json
from datetime import datetime, date, timedelta
from decimal import Decimal

from reporting.models import (
    Report, ReportDataSource, ReportField, ReportFilter,
    ReportJoin, ReportParameter, ReportExecution
)
from reporting.utils.model_inspector import DynamicModelInspector

logger = logging.getLogger(__name__)


class ReportQueryBuilder:
    """
    Builds and executes queries based on report definition.
    Handles complex joins, aggregations, and filtering.
    """

    def __init__(self, report: Report, user=None):
        self.report = report
        self.user = user
        self.inspector = DynamicModelInspector()
        self.query = None
        self.base_queryset = None
        self.annotations = {}
        self.aggregations = {}
        self.select_fields = []
        self.group_by_fields = []
        self.parameters = {}

    def build_query(self, parameters: Dict[str, Any] = None) -> models.QuerySet:
        """
        Build the QuerySet based on report definition.
        
        Args:
            parameters: Runtime parameters for the report
            
        Returns:
            Configured QuerySet ready for execution
        """
        self.parameters = parameters or {}

        # Step 1: Get primary data source and base queryset
        self._setup_base_queryset()

        # Step 2: Apply joins (select_related and prefetch_related)
        self._apply_joins()

        # Step 3: Apply filters
        self._apply_filters()

        # Step 4: Setup field selection and annotations
        self._setup_fields()

        # Step 5: Apply aggregations if needed
        self._apply_aggregations()

        # Step 6: Apply ordering
        self._apply_ordering()

        return self.query

    def execute(self, parameters: Dict[str, Any] = None,
                limit: int = None,
                offset: int = None,
                export_format: str = None) -> Dict[str, Any]:
        """
        Execute the query and return results with metadata.
        
        Args:
            parameters: Runtime parameters
            limit: Maximum number of rows
            offset: Number of rows to skip
            export_format: If specified, format for export
            
        Returns:
            Dictionary containing results and execution metadata
        """
        start_time = time.time()
        execution = None

        try:
            # Build the query
            query = self.build_query(parameters)

            # Apply pagination
            if offset:
                query = query[offset:]
            if limit:
                query = query[:limit]

            # Execute query
            if self.aggregations:
                # Aggregation query - returns dict
                results = query
                row_count = 1
                data = [results]  # Wrap in list for consistent format
            else:
                # Regular query - returns QuerySet
                results = list(query)
                row_count = len(results)
                data = self._serialize_results(results)

            execution_time = time.time() - start_time

            # Log execution
            execution = ReportExecution.objects.create(
                report=self.report,
                executed_by=self.user,
                parameters_used=self.parameters,
                execution_time=execution_time,
                row_count=row_count,
                status='success',
                export_format=export_format or '',
            )

            return {
                'success': True,
                'data': data,
                'row_count': row_count,
                'execution_time': execution_time,
                'execution_id': execution.id,
                'columns': self._get_column_info(),
                'parameters_used': self.parameters,
            }

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e)
            logger.error(f"Report execution error: {error_message}", exc_info=True)

            # Log failed execution
            if self.user:
                ReportExecution.objects.create(
                    report=self.report,
                    executed_by=self.user,
                    parameters_used=self.parameters,
                    execution_time=execution_time,
                    row_count=0,
                    status='error',
                    error_message=error_message,
                )

            return {
                'success': False,
                'error': error_message,
                'execution_time': execution_time,
            }

    def _setup_base_queryset(self):
        """Setup the base queryset from primary data source."""
        primary_source = self.report.data_sources.filter(is_primary=True).first()
        if not primary_source:
            raise ValueError("No primary data source defined for report")

        model_class = primary_source.get_model_class()
        if not model_class:
            raise ValueError(f"Model {primary_source.app_name}.{primary_source.model_name} not found")

        self.base_queryset = model_class.objects.all()
        self.query = self.base_queryset

        # Apply select_related from data source config
        if primary_source.select_related:
            self.query = self.query.select_related(*primary_source.select_related)

        # Apply prefetch_related from data source config
        if primary_source.prefetch_related:
            self.query = self.query.prefetch_related(*primary_source.prefetch_related)

    def _apply_joins(self):
        """Apply joins defined in the report."""
        # Note: Django doesn't support explicit SQL joins, but we can use
        # select_related and prefetch_related for optimization

        joins = self.report.joins.all().order_by('id')
        for join in joins:
            # For now, we'll add select_related for foreign keys
            # This is a simplified implementation
            if join.join_type in ['inner', 'left']:
                # Assuming the join is on a ForeignKey field
                field_path = join.left_field
                if '__' not in field_path and hasattr(self.query.model, field_path):
                    field = getattr(self.query.model, field_path)
                    if hasattr(field, 'field') and isinstance(field.field, models.ForeignKey):
                        self.query = self.query.select_related(field_path)

    def _apply_filters(self):
        """Apply all active filters to the query."""
        filters = self.report.filters.filter(is_active=True).order_by('group_order', 'id')

        # Group filters by logic group
        filter_groups = {}
        for filter_obj in filters:
            group_key = (filter_obj.logic_group, filter_obj.group_order)
            if group_key not in filter_groups:
                filter_groups[group_key] = []
            filter_groups[group_key].append(filter_obj)

        # Build Q objects for each group
        q_objects = []
        for (logic_op, _), group_filters in filter_groups.items():
            group_q = Q()

            for filter_obj in group_filters:
                filter_q = self._build_filter_q(filter_obj)
                if filter_q:
                    if logic_op == 'OR':
                        group_q |= filter_q
                    else:  # AND
                        group_q &= filter_q

            if group_q:
                q_objects.append(group_q)

        # Apply all Q objects to the query
        for q_obj in q_objects:
            self.query = self.query.filter(q_obj)

    def _build_filter_q(self, filter_obj: ReportFilter) -> Q:
        """Build a Q object for a single filter."""
        field_path = filter_obj.field_path
        operator = filter_obj.operator
        value = self._resolve_filter_value(filter_obj)

        if value is None and operator not in ['isnull', 'isnotnull']:
            return Q()  # Skip filter if value is None

        # Build the lookup
        if operator == 'eq':
            return Q(**{field_path: value})
        elif operator == 'ne':
            return ~Q(**{field_path: value})
        elif operator == 'gt':
            return Q(**{f"{field_path}__gt": value})
        elif operator == 'gte':
            return Q(**{f"{field_path}__gte": value})
        elif operator == 'lt':
            return Q(**{f"{field_path}__lt": value})
        elif operator == 'lte':
            return Q(**{f"{field_path}__lte": value})
        elif operator == 'in':
            return Q(**{f"{field_path}__in": value})
        elif operator == 'not_in':
            return ~Q(**{f"{field_path}__in": value})
        elif operator == 'contains':
            return Q(**{f"{field_path}__contains": value})
        elif operator == 'icontains':
            return Q(**{f"{field_path}__icontains": value})
        elif operator == 'startswith':
            return Q(**{f"{field_path}__startswith": value})
        elif operator == 'endswith':
            return Q(**{f"{field_path}__endswith": value})
        elif operator == 'regex':
            return Q(**{f"{field_path}__regex": value})
        elif operator == 'isnull':
            return Q(**{f"{field_path}__isnull": True})
        elif operator == 'isnotnull':
            return Q(**{f"{field_path}__isnull": False})
        elif operator == 'between':
            if isinstance(value, list) and len(value) == 2:
                return Q(**{f"{field_path}__range": value})
        elif operator == 'date_range':
            # Handle date range with start and end
            if isinstance(value, dict):
                start = value.get('start')
                end = value.get('end')
                if start and end:
                    return Q(**{f"{field_path}__range": [start, end]})

        return Q()

    def _resolve_filter_value(self, filter_obj: ReportFilter) -> Any:
        """Resolve the actual value for a filter based on its type."""
        value_type = filter_obj.value_type
        value = filter_obj.value

        if value_type == 'static':
            return value
        elif value_type == 'parameter':
            # Get value from parameters
            param_name = value
            return self.parameters.get(param_name)
        elif value_type == 'dynamic':
            # Evaluate dynamic value (e.g., "today", "current_user")
            return self._evaluate_dynamic_value(value)
        elif value_type == 'user_attribute':
            # Get attribute from current user
            if self.user and hasattr(self.user, value):
                return getattr(self.user, value)

        return value

    def _evaluate_dynamic_value(self, value: str) -> Any:
        """Evaluate dynamic values like 'today', 'current_month_start', etc."""
        today = timezone.now().date()

        dynamic_values = {
            'today': today,
            'yesterday': today - timedelta(days=1),
            'tomorrow': today + timedelta(days=1),
            'current_week_start': today - timedelta(days=today.weekday()),
            'current_week_end': today + timedelta(days=6 - today.weekday()),
            'current_month_start': today.replace(day=1),
            'current_month_end': (today.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
            'current_year_start': today.replace(month=1, day=1),
            'current_year_end': today.replace(month=12, day=31),
            'current_user_id': self.user.id if self.user else None,
            'current_user_email': self.user.email if self.user else None,
        }

        return dynamic_values.get(value, value)

    def _setup_fields(self):
        """Setup field selection and annotations."""
        visible_fields = self.report.fields.filter(is_visible=True).order_by('order')

        for field in visible_fields:
            field_path = field.field_path

            if field.aggregation and field.aggregation != 'group_by':
                # This is an aggregation field
                annotation_name = f"{field_path.replace('__', '_')}_{field.aggregation}"

                if field.aggregation == 'count':
                    self.annotations[annotation_name] = Count(field_path)
                elif field.aggregation == 'count_distinct':
                    self.annotations[annotation_name] = Count(field_path, distinct=True)
                elif field.aggregation == 'sum':
                    self.annotations[annotation_name] = Sum(field_path)
                elif field.aggregation == 'avg':
                    self.annotations[annotation_name] = Avg(field_path)
                elif field.aggregation == 'min':
                    self.annotations[annotation_name] = Min(field_path)
                elif field.aggregation == 'max':
                    self.annotations[annotation_name] = Max(field_path)

                self.aggregations[annotation_name] = field
            elif field.aggregation == 'group_by':
                # This is a grouping field
                self.group_by_fields.append(field_path)
                self.select_fields.append(field_path)
            else:
                # Regular field
                self.select_fields.append(field_path)

    def _apply_aggregations(self):
        """Apply aggregations and grouping to the query."""
        if self.annotations:
            # Apply annotations
            self.query = self.query.annotate(**self.annotations)

            if self.group_by_fields:
                # Apply grouping
                self.query = self.query.values(*self.group_by_fields)

                # Re-apply annotations after grouping
                self.query = self.query.annotate(**self.annotations)

                # Select all fields (grouped + aggregated)
                all_fields = self.group_by_fields + list(self.annotations.keys())
                self.query = self.query.values(*all_fields)
            else:
                # No grouping, just aggregate
                self.query = self.query.aggregate(**self.annotations)

    def _apply_ordering(self):
        """Apply ordering to the query."""
        # For now, we'll order by the display order of fields
        # In the future, this could be configurable
        if not self.aggregations:  # Don't order aggregation results
            ordering = []
            for field in self.report.fields.filter(is_visible=True).order_by('order'):
                if field.aggregation != 'group_by':
                    continue
                ordering.append(field.field_path)

            if ordering:
                self.query = self.query.order_by(*ordering)

    def _serialize_results(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Serialize query results to JSON-compatible format."""
        serialized = []

        for row in results:
            if isinstance(row, dict):
                # Already a dictionary (from values() query)
                serialized_row = {}
                for key, value in row.items():
                    serialized_row[key] = self._serialize_value(value)
                serialized.append(serialized_row)
            else:
                # Model instance
                serialized_row = {}

                # Get values for selected fields
                for field in self.report.fields.filter(is_visible=True).order_by('order'):
                    field_path = field.field_path
                    value = row

                    # Navigate through relationships
                    for part in field_path.split('__'):
                        if value is None:
                            break
                        if hasattr(value, part):
                            value = getattr(value, part)
                        else:
                            value = None

                    # Apply formatting
                    formatted_value = self._format_value(value, field)
                    serialized_row[field.display_name] = formatted_value

                serialized.append(serialized_row)

        return serialized

    def _serialize_value(self, value: Any) -> Any:
        """Convert a value to JSON-serializable format."""
        if value is None:
            return None
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, models.Model):
            return str(value)
        elif hasattr(value, '__dict__'):
            # Custom object
            return str(value)
        else:
            return value

    def _format_value(self, value: Any, field: ReportField) -> Any:
        """Apply formatting rules to a value."""
        if value is None:
            return None

        value = self._serialize_value(value)

        # Apply formatting from field configuration
        if field.formatting:
            format_type = field.formatting.get('type')

            if format_type == 'currency' and isinstance(value, (int, float)):
                prefix = field.formatting.get('prefix', '$')
                decimals = field.formatting.get('decimals', 2)
                return f"{prefix}{value:,.{decimals}f}"

            elif format_type == 'percentage' and isinstance(value, (int, float)):
                decimals = field.formatting.get('decimals', 1)
                return f"{value:.{decimals}f}%"

            elif format_type == 'date' and isinstance(value, str):
                # Value is already ISO format, could reformat if needed
                date_format = field.formatting.get('format', 'YYYY-MM-DD')
                # Implement date formatting logic here
                return value

            elif format_type == 'number' and isinstance(value, (int, float)):
                decimals = field.formatting.get('decimals', 0)
                use_commas = field.formatting.get('use_commas', True)
                if use_commas:
                    return f"{value:,.{decimals}f}"
                else:
                    return f"{value:.{decimals}f}"

        return value

    def _get_column_info(self) -> List[Dict[str, Any]]:
        """Get information about report columns."""
        columns = []

        for field in self.report.fields.filter(is_visible=True).order_by('order'):
            column = {
                'name': field.field_path,
                'display_name': field.display_name,
                'type': field.field_type,
                'aggregation': field.aggregation,
                'width': field.width,
                'formatting': field.formatting,
            }
            columns.append(column)

        return columns

    def get_sql(self) -> str:
        """Get the SQL that would be executed (for debugging)."""
        return str(self.query.query)