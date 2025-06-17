import traceback

from django.db import transaction

from case.models import CaseMapper, MapperExecutionLog
from case.plugins.default_plugin import load_function_by_path


def preview_mapping(case):
    """
    Runs the mapping logic in read-only (dry-run) mode.
    Returns a list of simulated changes for each target.
    """
    from case.models import CaseMapper
    preview_results = []

    try:
        mapper = CaseMapper.objects.get(case_type=case.case_type)
    except CaseMapper.DoesNotExist:
        return [{"error": f"No CaseMapper found for case_type={case.case_type}"}]

    if not mapper.active_ind:
        print(f"Mapper {mapper.name} is inactive.")
        return

    for target in mapper.targets.filter(active_ind=True):
        # Load plugins or fallbacks
        finder_func = load_function_by_path(
            target.finder_function_path
        ) if target.finder_function_path else load_function_by_path(
            "myapp.plugins.default_plugin.find_records"
        )

        processor_func = load_function_by_path(
            target.processor_function_path
        ) if target.processor_function_path else load_function_by_path(
            "myapp.plugins.default_plugin.process_records"
        )

        # Call finder
        found_objects = finder_func(case, target)

        # Step: Call the main processor
        if found_objects is None:
            updated = processor_func(case, target, None)
        elif isinstance(found_objects, list) or hasattr(found_objects, 'exists'):
            updated = processor_func(case, target, found_objects)
        else:
            updated = processor_func(case, target, found_objects)

        # ✅ NEW: Run post_processor if defined
        if target.post_processor_path:
            try:
                post_processor = load_function_by_path(target.post_processor_path)
                post_processor(case=case, target=target, result=updated)
            except Exception as e:
                print(f"[Warning] Post-processor failed for {target}: {str(e)}")

        # Run dry_run if plugin supports it
        if hasattr(processor_func, "dry_run"):
            try:
                result = processor_func.dry_run(case, target, found_objects)
            except Exception as e:
                result = {
                    "target": str(target),
                    "error": f"dry_run failed: {str(e)}"
                }
        else:
            result = {
                "target": str(target),
                "warning": "Processor does not support dry_run()"
            }

        preview_results.append(result)

    return preview_results


import traceback
from django.db import transaction
from django.utils import timezone

from case.models import CaseMapper, MapperExecutionLog
from case.plugins.default_plugin import load_function_by_path


def execute_mappings(case):
    """
    Executes all active mapping targets for the given case in a single atomic transaction.
    If any target fails, the whole operation rolls back.
    Also logs each execution attempt to MapperExecutionLog.
    """
    try:
        mapper = CaseMapper.objects.get(case_type=case.case_type, active_ind=True)
    except CaseMapper.DoesNotExist:
        print(f"[Mapper] ❌ No active CaseMapper found for case_type={case.case_type}")
        return

    with transaction.atomic():
        for target in mapper.targets.filter(active_ind=True):
            try:
                print(f"[Mapper] ▶ Executing target: {target}")

                finder_func = load_function_by_path(
                    target.finder_function_path
                ) if target.finder_function_path else load_function_by_path(
                    "myapp.plugins.default_plugin.find_records"
                )

                processor_func = load_function_by_path(
                    target.processor_function_path
                ) if target.processor_function_path else load_function_by_path(
                    "myapp.plugins.default_plugin.process_records"
                )

                found_objects = finder_func(case, target)

                if found_objects is None:
                    updated = processor_func(case, target, None)
                elif isinstance(found_objects, list) or hasattr(found_objects, 'exists'):
                    updated = processor_func(case, target, found_objects)
                else:
                    updated = processor_func(case, target, found_objects)

                # ✅ Post-mapping hook
                if target.post_processor_path:
                    post_func = load_function_by_path(target.post_processor_path)
                    post_func(case=case, target=target, result=updated)

                # ✅ Log success
                MapperExecutionLog.objects.create(
                    case=case,
                    mapper_target=target,
                    executed_at=timezone.now(),
                    success=True,
                    result_data={
                        "model": str(target.content_type),
                        "object": str(updated.pk if hasattr(updated, "pk") else updated),
                    }
                )

                print(f"[Mapper] ✅ Target processed successfully: {target}")

            except Exception as e:
                error_msg = str(e)
                traceback.print_exc()

                # ✅ Log failure
                MapperExecutionLog.objects.create(
                    case=case,
                    mapper_target=target,
                    executed_at=timezone.now(),
                    success=False,
                    error_message=error_msg
                )

                raise  # 🔁 Still raise to trigger rollback

    print("[Mapper] ✅ All mapping targets completed successfully.")
