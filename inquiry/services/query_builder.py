import time
from typing import Dict, List, Any, Optional, Tuple
from django.db.models import Q, QuerySet, Prefetch, Count, Sum, Avg, Min, Max
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from jsonpath_ng import parse

class DynamicQueryBuilder:
    def __init__(self, inquiry_config):
        self.inquiry = inquiry_config
        self.model = inquiry_config.content_type.model_class()
        self.query_count = 0

    def build_queryset(
            self,
            filters: Optional[Dict] = None,
            search: Optional[str] = None,
            sort: Optional[List] = None,
            user: Optional[Any] = None
    ) -> QuerySet:
        """Build queryset based on configuration"""
        start_time = time.time()

        queryset = self.model.objects.all()

        # Apply select_related and prefetch_related
        queryset = self._optimize_query(queryset)

        # Apply base permissions
        if user and not self.inquiry.is_public:
            queryset = self._apply_base_permissions(queryset, user)

        # Apply configured filters
        if filters:
            queryset = self._apply_filters(queryset, filters)

        # Apply default filters
        queryset = self._apply_default_filters(queryset)

        # Apply search
        if search and self.inquiry.enable_search:
            queryset = self._apply_search(queryset, search)

        # Apply sorting
        if sort:
            queryset = self._apply_custom_sorting(queryset, sort)
        else:
            queryset = self._apply_default_sorting(queryset)

        # Apply distinct if configured
        if self.inquiry.distinct:
            queryset = queryset.distinct()

        # Track query count
        self.query_count = len(connection.queries) - self.query_count

        return queryset

    def _optimize_query(self, queryset: QuerySet) -> QuerySet:
        """Add select_related and prefetch_related"""
        select_related = []
        prefetch_related = []

        for relation in self.inquiry.relations.all():
            if relation.use_select_related:
                select_related.append(relation.relation_path)
            elif relation.use_prefetch_related:
                # Handle nested prefetch if needed
                if relation.include_count:
                    prefetch_obj = Prefetch(
                        relation.relation_path,
                        queryset=self._get_related_queryset(relation)
                    )
                    prefetch_related.append(prefetch_obj)
                else:
                    prefetch_related.append(relation.relation_path)

        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)

        return queryset

    def _get_related_queryset(self, relation):
        """Get queryset for related model with field filtering"""
        path_parts = relation.relation_path.split('__')
        related_model = self.model

        for part in path_parts:
            field = related_model._meta.get_field(part)
            related_model = field.related_model

        related_qs = related_model.objects.all()

        # Apply field filtering if configured
        if relation.include_fields:
            # This would need custom implementation based on your needs
            pass

        return related_qs

    def _apply_filters(self, queryset: QuerySet, filters: Dict) -> QuerySet:
        """Apply user-provided filters"""
        for filter_code, value in filters.items():
            try:
                filter_config = self.inquiry.filters.get(code=filter_code)
                lookup = f"{filter_config.field_path}__{filter_config.operator}"

                # Handle special operators
                if filter_config.operator == 'isnull':
                    queryset = queryset.filter(**{filter_config.field_path + '__isnull': value})
                elif filter_config.operator == 'isnotnull':
                    queryset = queryset.filter(**{filter_config.field_path + '__isnull': False})
                elif filter_config.operator == 'range' and isinstance(value, list) and len(value) == 2:
                    queryset = queryset.filter(**{filter_config.field_path + '__range': value})
                else:
                    queryset = queryset.filter(**{lookup: value})

            except self.inquiry.filters.model.DoesNotExist:
                # Handle dynamic filters
                if '__' in filter_code:
                    queryset = queryset.filter(**{filter_code: value})

        return queryset

    def _apply_default_filters(self, queryset: QuerySet) -> QuerySet:
        """Apply default filters from configuration"""
        for filter_config in self.inquiry.filters.filter(
                default_value__isnull=False,
                is_visible=True
        ):
            if filter_config.default_value is not None:
                lookup = f"{filter_config.field_path}__{filter_config.operator}"
                queryset = queryset.filter(**{lookup: filter_config.default_value})

        return queryset

    def _apply_search(self, queryset: QuerySet, search: str) -> QuerySet:
        """Apply global search across configured fields"""
        search_fields = self.inquiry.search_fields or []

        # Add searchable fields from field configuration
        for field in self.inquiry.fields.filter(is_searchable=True):
            search_fields.append(field.field_path)

        if search_fields:
            q_objects = Q()
            for field in search_fields:
                q_objects |= Q(**{f"{field}__icontains": search})
            queryset = queryset.filter(q_objects)

        return queryset

    def _apply_custom_sorting(self, queryset: QuerySet, sort: List) -> QuerySet:
        """Apply user-provided sorting"""
        order_by = []
        for sort_item in sort:
            if isinstance(sort_item, dict):
                field = sort_item.get('field')
                direction = sort_item.get('direction', 'asc')
            else:
                field = sort_item
                direction = 'asc'

            # Verify field is sortable
            field_config = self.inquiry.fields.filter(
                field_path=field,
                is_sortable=True
            ).first()

            if field_config:
                if direction == 'desc':
                    order_by.append(f"-{field}")
                else:
                    order_by.append(field)

        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset

    def _apply_default_sorting(self, queryset: QuerySet) -> QuerySet:
        """Apply default sorting from configuration"""
        order_by = []
        for sort in self.inquiry.sorts.all():
            if sort.direction == 'desc':
                order_by.append(f"-{sort.field_path}")
            else:
                order_by.append(sort.field_path)

        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset

    def _apply_base_permissions(self, queryset: QuerySet, user) -> QuerySet:
        """Apply base permission filtering"""
        user_groups = user.groups.all()

        # Check if user has permission to view this inquiry
        if not self.inquiry.allowed_groups.filter(id__in=user_groups).exists():
            if not user.is_superuser:
                return queryset.none()

        # Apply row-level permissions if configured
        permission = self.inquiry.permissions.filter(
            group__in=user_groups
        ).first()

        if permission and not permission.can_view_all:
            # Apply ownership filter if model has user field
            if hasattr(self.model, 'created_by'):
                queryset = queryset.filter(created_by=user)
            elif hasattr(self.model, 'user'):
                queryset = queryset.filter(user=user)
            elif hasattr(self.model, 'owner'):
                queryset = queryset.filter(owner=user)

        return queryset

    def get_aggregations(self, queryset: QuerySet) -> Dict:
        """Calculate aggregations for fields"""
        aggregations = {}

        for field in self.inquiry.fields.filter(aggregation__isnull=False):
            agg_type = field.aggregation
            field_path = field.field_path

            if agg_type == 'count':
                aggregations[f"{field_path}__count"] = Count(field_path)
            elif agg_type == 'sum':
                aggregations[f"{field_path}__sum"] = Sum(field_path)
            elif agg_type == 'avg':
                aggregations[f"{field_path}__avg"] = Avg(field_path)
            elif agg_type == 'min':
                aggregations[f"{field_path}__min"] = Min(field_path)
            elif agg_type == 'max':
                aggregations[f"{field_path}__max"] = Max(field_path)

        if aggregations:
            return queryset.aggregate(**aggregations)
        return {}