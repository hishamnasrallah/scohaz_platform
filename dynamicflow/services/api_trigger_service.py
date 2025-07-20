# dynamicflow/services/api_trigger_service.py
import json
import logging
import time
from typing import Dict, Any, List, Optional
from jsonpath_ng import jsonpath, parse
from django.db import models
from django.db.models import QuerySet
from django.core.cache import cache
from django.conf import settings
from integration.models import Integration
from celery import shared_task

logger = logging.getLogger(__name__)


class APITriggerService:
    """
    Service to handle dynamic API call triggering based on field configurations.
    """

    @staticmethod
    def _resolve_json_path(data: Any, path: str) -> Any:
        """
        Resolves a JSONPath expression against the given data.
        Handles special paths like '$.instance.pk', '$.case_data', etc.
        """
        if path.startswith('$.instance.'):
            # Special handling for Django model instance attributes
            attr_path = path[len('$.instance.'):]
            parts = attr_path.split('.')
            value = data  # 'data' here is the model instance
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                    if callable(value):  # Handle methods
                        value = value()
                else:
                    return None
            return value
        elif path.startswith('$.case_data.'):
            # Extract from case_data JSON field
            field_path = path[len('$.case_data.'):]
            if isinstance(data, dict) and 'case_data' in data:
                return APITriggerService._get_nested_value(data['case_data'], field_path)
            return None
        elif path.startswith('$.old_case_data.') or path.startswith('$.new_case_data.'):
            # For data within the flow (old/new)
            try:
                jsonpath_expr = parse(path)
                match = jsonpath_expr.find(data)
                return match[0].value if match else None
            except Exception as e:
                logger.warning(f"Invalid JSONPath expression '{path}': {e}")
                return None
        else:
            # Assume it's a direct value or simple key
            return data.get(path) if isinstance(data, dict) else data

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    @staticmethod
    def _evaluate_condition(condition_expr: str, context: Dict[str, Any]) -> bool:
        """
        Evaluates a simple Python-like expression for a condition.
        Uses a safe evaluation approach.
        """
        if not condition_expr:
            return True  # No condition means always true

        # Replace JSONPath-like references with actual values from context
        processed_expr = condition_expr
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                processed_expr = processed_expr.replace(f"$.{key}", repr(value))
            elif value is None:
                processed_expr = processed_expr.replace(f"$.{key}", "None")

        try:
            # Use eval with a restricted global/local scope for safety
            # For production, consider using a dedicated safe expression evaluator
            return eval(processed_expr, {"__builtins__": None}, context)
        except Exception as e:
            logger.error(f"Error evaluating condition expression '{condition_expr}': {e}")
            return False

    @staticmethod
    def _construct_payload(mapping: Dict[str, str], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Constructs a payload (body, query_params, headers) based on a mapping.
        """
        payload = {}
        for api_key, source_path in mapping.items():
            resolved_value = APITriggerService._resolve_json_path(context, source_path)
            payload[api_key] = resolved_value
        return payload

    @staticmethod
    def _check_rate_limit(integration_id: int, case_id: int) -> bool:
        """
        Check if API call is within rate limits.
        """
        cache_key = f"api_rate_limit:{integration_id}:{case_id}"
        current_count = cache.get(cache_key, 0)

        max_calls = getattr(settings, 'API_TRIGGER_RATE_LIMIT', 10)  # 10 calls per minute

        if current_count >= max_calls:
            return False

        cache.set(cache_key, current_count + 1, 60)  # 60 second window
        return True

    @staticmethod
    def _trigger_single_api_call(config: Dict[str, Any], context: Dict[str, Any],
                                 field_id: int = None, case_id: int = None):
        """
        Triggers a single API call based on its configuration.
        """
        from case.models import APICallLog

        integration_id = config.get("integration_id")
        if not integration_id:
            logger.error(f"API call config missing 'integration_id': {config}")
            return

        # Check rate limiting
        if case_id and not APITriggerService._check_rate_limit(integration_id, case_id):
            logger.warning(f"Rate limit exceeded for integration {integration_id} and case {case_id}")
            return

        try:
            integration = Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            logger.error(f"Integration with ID {integration_id} not found for API call.")
            return

        # Evaluate condition before making the call
        condition_expr = config.get("condition")
        if condition_expr and not APITriggerService._evaluate_condition(condition_expr, context):
            logger.info(f"API call '{config.get('id', 'unnamed')}' skipped due to condition.")
            return

        # Construct payloads
        payload_body = APITriggerService._construct_payload(
            config.get("payload_mapping", {}), context
        )
        query_params = APITriggerService._construct_payload(
            config.get("query_param_mapping", {}), context
        )
        headers = APITriggerService._construct_payload(
            config.get("headers_mapping", {}), context
        )

        # Log the API call attempt
        start_time = time.time()

        if config.get("async", False):
            # Async call using Celery
            APITriggerService._trigger_api_call_async.delay(
                integration.id, payload_body, query_params, headers, case_id, field_id
            )
            logger.info(f"API call '{config.get('id', 'unnamed')}' scheduled asynchronously.")
        else:
            # Synchronous call
            try:
                response = integration.make_api_request(
                    body=payload_body, query_params=query_params, headers=headers
                )
                duration_ms = int((time.time() - start_time) * 1000)

                # Log successful call
                if case_id and field_id:
                    APICallLog.objects.create(
                        case_id=case_id,
                        field_id=field_id,
                        integration=integration,
                        event_type=config.get("event", "unknown"),
                        request_data={
                            'body': payload_body,
                            'query_params': query_params,
                            'headers': headers
                        },
                        response_data=response,
                        status_code=200,
                        success=True,
                        duration_ms=duration_ms
                    )

                logger.info(f"API call '{config.get('id', 'unnamed')}' successful: {response}")
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                # Log failed call
                if case_id and field_id:
                    APICallLog.objects.create(
                        case_id=case_id,
                        field_id=field_id,
                        integration=integration,
                        event_type=config.get("event", "unknown"),
                        request_data={
                            'body': payload_body,
                            'query_params': query_params,
                            'headers': headers
                        },
                        success=False,
                        error_message=str(e),
                        duration_ms=duration_ms
                    )

                logger.error(f"API call '{config.get('id', 'unnamed')}' failed: {e}")

    @staticmethod
    @shared_task(bind=True, max_retries=3)
    def _trigger_api_call_async(self, integration_id: int, body: Dict, query_params: Dict,
                                headers: Dict, case_id: int = None, field_id: int = None):
        """
        Celery task to make an API call asynchronously with retry logic.
        """
        from case.models import APICallLog
        from integration.models import Integration

        start_time = time.time()

        try:
            integration = Integration.objects.get(id=integration_id)
            response = integration.make_api_request(
                body=body, query_params=query_params, headers=headers
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful call
            if case_id and field_id:
                APICallLog.objects.create(
                    case_id=case_id,
                    field_id=field_id,
                    integration=integration,
                    event_type='async',
                    request_data={
                        'body': body,
                        'query_params': query_params,
                        'headers': headers
                    },
                    response_data=response,
                    status_code=200,
                    success=True,
                    duration_ms=duration_ms
                )

            logger.info(f"Async API call to {integration.name} successful: {response}")
            return response

        except Integration.DoesNotExist:
            logger.error(f"Integration {integration_id} not found")
            raise

        except Exception as e:
            logger.error(f"Async API call to {integration_id} failed: {e}")

            # Log failed call
            if case_id and field_id:
                APICallLog.objects.create(
                    case_id=case_id,
                    field_id=field_id,
                    integration_id=integration_id,
                    event_type='async',
                    request_data={
                        'body': body,
                        'query_params': query_params,
                        'headers': headers
                    },
                    success=False,
                    error_message=str(e),
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    @staticmethod
    def trigger_api_calls(
            field: 'Field',  # The Field object
            event: str,
            case_data: Dict[str, Any],  # Current case_data from the Case model
            instance: Optional[models.Model] = None,  # The Case instance
            old_case_data: Optional[Dict[str, Any]] = None  # Previous case_data
    ):
        """
        Triggers API calls for a given field and event.
        """
        if not field._api_call_config:
            return

        field_value = case_data.get(field._field_name)

        for config in field._api_call_config:
            if config.get("event") == event:
                context = {
                    "case_data": case_data,
                    "field_name": field._field_name,
                    "field_value": field_value,
                    "instance": instance,
                    "old_case_data": old_case_data,
                    "old_field_value": old_case_data.get(field._field_name) if old_case_data else None
                }
                APITriggerService._trigger_single_api_call(
                    config, context, field.id, instance.id if instance else None
                )

    @staticmethod
    def trigger_on_change_for_field(
            field: 'Field',
            old_value: Any,
            new_value: Any,
            full_old_data: Dict[str, Any],
            full_new_data: Dict[str, Any],
            instance: Optional[models.Model] = None
    ):
        """
        Triggers 'on_change' API calls for a specific field if its value has changed.
        """
        if old_value == new_value:
            return  # No change, no trigger

        for config in field._api_call_config:
            if config.get("event") == "on_change":
                context = {
                    "field_name": field._field_name,
                    "old_value": old_value,
                    "new_value": new_value,
                    "case_data": full_new_data,  # Current case_data
                    "old_case_data": full_old_data,  # Previous case_data
                    "instance": instance  # The Case instance
                }
                APITriggerService._trigger_single_api_call(
                    config, context, field.id, instance.id if instance else None
                )
