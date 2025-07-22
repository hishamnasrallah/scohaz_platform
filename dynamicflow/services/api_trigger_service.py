# dynamicflow/services/api_trigger_service.py - Updated version

import json
import logging
import time
from typing import Dict, Any, Optional
from django.db import models
from django.core.cache import cache
from django.conf import settings
from celery import shared_task

from case.models import APICallLog
from integration.models import Integration
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


# 1. Update prepare_request_data in FieldIntegration model to return 4 values instead of 3:

class FieldIntegration(models.Model):
    # ... existing fields ...

    def prepare_request_data(self, case_data, field_value):
        """
        Enhanced to also prepare path parameters.
        """
        def get_value(data, path):
            """Extract value from data using dot notation"""
            if path == 'field_value':
                return field_value

            keys = path.split('.')
            current = data
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current

        # Prepare payload
        payload = {}
        for api_key, case_key in self.payload_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                payload[api_key] = value

        # Prepare query params
        query_params = {}
        for api_key, case_key in self.query_param_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                query_params[api_key] = value

        # Prepare headers
        headers = {}
        for api_key, case_key in self.header_mapping.items():
            value = get_value(case_data, case_key)
            if value is not None:
                headers[api_key] = str(value)

        # NEW: Prepare path parameters
        path_param_config = self.path_param_mapping or self.integration.path_param_mapping
        path_params = {}
        for param_name, case_key in path_param_config.items():
            value = get_value(case_data, case_key)
            if value is not None:
                path_params[param_name] = value

        return payload, query_params, headers, path_params  # Now returns 4 values


# 2. Update your APITriggerService to handle path parameters:

class APITriggerService:
    """
    Service to handle dynamic API call triggering based on field integrations.
    """
    @staticmethod
    def trigger_api_calls(
            field: 'Field',
            event: str,
            case_data: Dict[str, Any],
            instance: Optional[models.Model] = None,
            old_case_data: Optional[Dict[str, Any]] = None
    ):
        """
        Triggers all API calls configured for a field and event.
        """
        from integration.models import FieldIntegration
        from case.models import APICallLog

        # Get the field value from case_data
        field_value = case_data.get(field._field_name)

        # Get all integrations for this field and event
        integrations = field.get_integrations_for_event(event)

        for field_integration in integrations:
            # Check if integration should execute
            if not field_integration.should_execute(field_value, case_data):
                logger.info(f"Skipping integration {field_integration} due to condition")
                continue

            # Check rate limiting
            if instance and not APITriggerService._check_rate_limit(
                    field_integration.integration.id, instance.id
            ):
                logger.warning(
                    f"Rate limit exceeded for integration {field_integration.integration.id}"
                )
                continue

            # UPDATED: Prepare request data - now returns 4 values
            payload, query_params, headers, path_params = field_integration.prepare_request_data(
                case_data, field_value
            )

            # Log the attempt
            start_time = time.time()

            if field_integration.is_async:
                # UPDATED: Async execution - pass path_params
                APITriggerService._execute_integration_async.delay(
                    field_integration.id,
                    payload,
                    query_params,
                    headers,
                    path_params,  # NEW parameter
                    instance.id if instance else None,
                    case_data
                )
                logger.info(f"Integration {field_integration} scheduled asynchronously")
            else:
                # Sync execution
                try:
                    # UPDATED: Pass path_params to make_api_request
                    response = field_integration.integration.make_api_request(
                        body=payload,
                        query_params=query_params,
                        headers=headers,
                        path_params=path_params  # NEW parameter
                    )
                    duration_ms = int((time.time() - start_time) * 1000)

                    # UPDATED: Log successful call - include path_params
                    if instance:
                        APICallLog.objects.create(
                            case_id=instance.id,
                            field_id=field.id,
                            integration=field_integration.integration,
                            event_type=event,
                            request_data={
                                'body': payload,
                                'query_params': query_params,
                                'headers': headers,
                                'path_params': path_params  # NEW
                            },
                            response_data=response,
                            status_code=200,
                            success=True,
                            duration_ms=duration_ms
                        )

                    # Handle response updates if configured
                    if field_integration.update_field_on_response and instance:
                        APITriggerService._handle_response_updates(
                            field_integration, response, instance, case_data
                        )

                    logger.info(f"Integration {field_integration} executed successfully")

                except Exception as e:
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Log failed call
                    if instance:
                        APICallLog.objects.create(
                            case_id=instance.id,
                            field_id=field.id,
                            integration=field_integration.integration,
                            event_type=event,
                            request_data={
                                'body': payload,
                                'query_params': query_params,
                                'headers': headers,
                                'path_params': path_params  # NEW
                            },
                            success=False,
                            error_message=str(e),
                            duration_ms=duration_ms
                        )

                    logger.error(f"Integration {field_integration} failed: {e}")
    @staticmethod
    def _extract_mapped_data(mapping_config: Dict[str, str], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to extract values from source_data based on a mapping configuration.
        Mapping config: {'api_key': 'case_data_path'}
        """
        extracted_data = {}
        for api_key, case_data_path in mapping_config.items():
            # Simple dot notation for now, can be extended for complex JSONPath
            parts = case_data_path.split('.')
            current_value = source_data
            found = True
            for part in parts:
                if isinstance(current_value, dict) and part in current_value:
                    current_value = current_value[part]
                else:
                    found = False
                    break
            if found:
                extracted_data[api_key] = current_value
        return extracted_data

    @staticmethod
    def trigger_integration_from_action(
            integration: Integration,
            case_instance: 'Case',
            user: User,
            event_type: str = "action_triggered"
    ):
        """
        Triggers a specific Integration directly from an Action.
        Dynamically populates request data using mappings defined on the Integration model.
        """
        start_time = time.time()
        case_data = case_instance.case_data or {}

        # Prepare request data based on Integration's mapping fields
        payload = APITriggerService._extract_mapped_data(integration.payload_mapping, case_data)
        query_params = APITriggerService._extract_mapped_data(integration.query_param_mapping, case_data)
        headers = APITriggerService._extract_mapped_data(integration.header_mapping, case_data)
        path_params = APITriggerService._extract_mapped_data(integration.path_param_mapping, case_data)

        # Log the attempt
        request_log_data = {
            'body': payload,
            'query_params': query_params,
            'headers': headers,
            'path_params': path_params
        }

        try:
            # Make the API request
            response = integration.make_api_request(
                body=payload,
                query_params=query_params,
                headers=headers,
                path_params=path_params
            )
            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful call
            APICallLog.objects.create(
                case=case_instance,
                # field=None, # No specific field triggered this
                integration=integration,
                event_type=event_type,
                request_data=request_log_data,
                response_data=response,
                status_code=200,
                success=True,
                duration_ms=duration_ms
            )
            logger.info(f"Integration '{integration.name}' triggered by action for Case {case_instance.id} successfully.")

            # Handle response mapping if needed (similar to FieldIntegration)
            if integration.response_mapping:
                # This part needs to be implemented based on your response_mapping logic
                # For example, update case_instance.case_data based on response_mapping
                pass

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Integration '{integration.name}' triggered by action for Case {case_instance.id} failed: {e}")

            # Log failed call
            APICallLog.objects.create(
                case=case_instance,
                # field=None,
                integration=integration,
                event_type=event_type,
                request_data=request_log_data,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
            # Optionally re-raise or handle retry logic here
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

        # Trigger with the on_change event
        APITriggerService.trigger_api_calls(
            field=field,
            event='on_change',
            case_data=full_new_data,
            instance=instance,
            old_case_data=full_old_data
        )

    @staticmethod
    def _check_rate_limit(integration_id: int, case_id: int) -> bool:
        """Check if API call is within rate limits."""
        cache_key = f"api_rate_limit:{integration_id}:{case_id}"
        current_count = cache.get(cache_key, 0)

        max_calls = getattr(settings, 'API_TRIGGER_RATE_LIMIT', 10)

        if current_count >= max_calls:
            return False

        cache.set(cache_key, current_count + 1, 60)
        return True

    @staticmethod
    def _handle_response_updates(field_integration, response, instance, case_data):
        """
        Handle updating fields based on API response
        """
        from jsonpath_ng import parse

        try:
            # Update the main field if configured
            if field_integration.response_field_path:
                jsonpath_expr = parse(field_integration.response_field_path)
                matches = jsonpath_expr.find(response)
                if matches:
                    new_value = matches[0].value
                    case_data[field_integration.field._field_name] = new_value
                    instance.case_data[field_integration.field._field_name] = new_value

            # Update additional mapped fields
            for response_path, case_field in field_integration.response_field_mapping.items():
                jsonpath_expr = parse(f"$.{response_path}")
                matches = jsonpath_expr.find(response)
                if matches:
                    instance.case_data[case_field] = matches[0].value

            instance.save()

        except Exception as e:
            logger.error(f"Error updating fields from response: {e}")

    @staticmethod
    @shared_task(bind=True, max_retries=3)
    def _execute_integration_async(
            self,
            field_integration_id: int,
            payload: Dict,
            query_params: Dict,
            headers: Dict,
            path_params: Dict,  # NEW parameter
            case_id: Optional[int] = None,
            case_data: Optional[Dict] = None
    ):
        """
        Celery task to execute integration asynchronously with retry logic.
        """
        from integration.models import FieldIntegration
        from case.models import APICallLog, Case

        start_time = time.time()

        try:
            field_integration = FieldIntegration.objects.select_related(
                'integration', 'field'
            ).get(id=field_integration_id)

            # UPDATED: Pass path_params
            response = field_integration.integration.make_api_request(
                body=payload,
                query_params=query_params,
                headers=headers,
                path_params=path_params  # NEW
            )

            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful call
            if case_id:
                APICallLog.objects.create(
                    case_id=case_id,
                    field_id=field_integration.field.id,
                    integration=field_integration.integration,
                    event_type=field_integration.trigger_event,
                    request_data={
                        'body': payload,
                        'query_params': query_params,
                        'headers': headers,
                        'path_params': path_params  # NEW
                    },
                    response_data=response,
                    status_code=200,
                    success=True,
                    duration_ms=duration_ms
                )

                # Handle response updates if configured
                if field_integration.update_field_on_response and case_id:
                    case = Case.objects.get(id=case_id)
                    APITriggerService._handle_response_updates(
                        field_integration, response, case, case_data or case.case_data
                    )

            logger.info(f"Async integration {field_integration} executed successfully")
            return response

        except Exception as e:
            logger.error(f"Async integration failed: {e}")

            # Log failed call
            if case_id:
                APICallLog.objects.create(
                    case_id=case_id,
                    field_id=field_integration.field.id,
                    integration_id=field_integration.integration.id,
                    event_type=field_integration.trigger_event,
                    request_data={
                        'body': payload,
                        'query_params': query_params,
                        'headers': headers,
                        'path_params': path_params  # NEW
                    },
                    success=False,
                    error_message=str(e),
                    duration_ms=int((time.time() - start_time) * 1000)
                )

            # Retry with exponential backoff
            retry_delay = field_integration.integration.retry_delay * (self.request.retries + 1)
            raise self.retry(exc=e, countdown=retry_delay)