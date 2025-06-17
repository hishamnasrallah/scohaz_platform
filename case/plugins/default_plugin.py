# myapp/plugins/default_plugin.py


def find_records(case, mapper_target):
    """
    A trivial default finder that does no real searching.
    Always returns None (no existing record found).
    """
    return None


# myapp/plugins/default_plugin.py

def process_records(case, mapper_target, found_object=None, depth=0, depth_limit=10, visited_targets=None, context=None):
    """
    Processes a MapperTarget and its children recursively with full context injection.
    """
    from case.models import MapperTarget, MapperExecutionLog
    from lookup.models import Lookup
    context = context or {}

    if visited_targets is None:
        visited_targets = set()

    if depth > depth_limit:
        raise RecursionError(f"Maximum depth limit ({depth_limit}) reached at target {mapper_target}")

    if mapper_target.id in visited_targets:
        raise RecursionError(f"Circular reference detected in MapperTarget ID {mapper_target.id}")

    visited_targets.add(mapper_target.id)

    model_class = mapper_target.content_type.model_class()
    field_rules = mapper_target.field_rules.all()
    results = []

    try:
        # 🟢 List-based mapping
        if mapper_target.root_path:
            data_list = extract_json_value(case.case_data, mapper_target.root_path)
            if not isinstance(data_list, list):
                raise ValueError(f"Expected list at root_path '{mapper_target.root_path}', got: {type(data_list)}")

            filter_func = None
            if mapper_target.filter_function_path:
                filter_func = load_function_by_path(mapper_target.filter_function_path)

            for index, item in enumerate(data_list):
                if filter_func:
                    try:
                        if not filter_func(item, case):
                            continue
                    except Exception as e:
                        raise ValueError(f"Filter function failed on item #{index}: {e}")

                instance = model_class()
                runtime_context = {
                    **context,
                    "case_id": case.id,
                    "record_index": index,
                    "parent_object": context.get("current_object"),
                    "current_data": item,
                }

                log = apply_field_rules(instance, item, field_rules, context=runtime_context)
                instance.save()

                MapperExecutionLog.objects.create(
                    case=case,
                    mapper_target=mapper_target,
                    success=True,
                    result_data={
                        "target_model": model_class.__name__,
                        "record_index": index,
                        "fields": log
                    }
                )

                results.append(instance)

                # 🔁 Child recursive execution
                child_targets = MapperTarget.objects.filter(parent_target=mapper_target)
                for child in child_targets:
                    process_records(
                        case=case,
                        mapper_target=child,
                        found_object=None,
                        depth=depth + 1,
                        depth_limit=depth_limit,
                        visited_targets=visited_targets.copy(),
                        context={
                            **runtime_context,
                            "current_object": instance
                        }
                    )

        # 🟢 Flat mapping
        else:
            data_context = context.get("current_data") or case.case_data
            instance = found_object or model_class()

            runtime_context = {
                **context,
                "case_id": case.id,
                "current_data": data_context,
                "current_object": instance
            }

            log = apply_field_rules(instance, data_context, field_rules, context=runtime_context)
            instance.save()

            MapperExecutionLog.objects.create(
                case=case,
                mapper_target=mapper_target,
                success=True,
                result_data={
                    "target_model": model_class.__name__,
                    "fields": log
                }
            )

            results.append(instance)

            # 🔁 Process children with full context
            child_targets = MapperTarget.objects.filter(parent_target=mapper_target)
            for child in child_targets:
                process_records(
                    case=case,
                    mapper_target=child,
                    found_object=None,
                    depth=depth + 1,
                    depth_limit=depth_limit,
                    visited_targets=visited_targets.copy(),
                    context={
                        **runtime_context,
                        "current_object": instance
                    }
                )

    except Exception as e:
        MapperExecutionLog.objects.create(
            case=case,
            mapper_target=mapper_target,
            success=False,
            error_trace=str(e)
        )
        raise e

    return results


def apply_field_rules(instance, data_source, rules, context=None):
    """
    Applies rules with expression/legacy condition + lookup + transform support.
    Context is injected into all evaluators and transformers.
    """
    from case.utils.expression_evaluator import eval_expression, UnsafeExpressionError
    from lookup.models import Lookup

    execution_log = []
    context = context or {}

    for rule in rules:
        original_value = extract_json_value(data_source, rule.json_path)
        value = original_value
        condition_matched = True
        was_transformed = False

        # ✅ Multi-condition logic (grouped)
        conditions = rule.conditions.all()
        grouped = {}
        for cond in conditions:
            grouped.setdefault(cond.group, []).append(cond)

        group_results = []

        for group_name, group_conds in grouped.items():
            sub_result = True
            for cond in group_conds:
                result = True
                try:
                    if cond.condition_expression:
                        result = eval_expression(cond.condition_expression, {**data_source, **context})
                    elif cond.condition_path and cond.condition_operator:
                        val = extract_json_value(data_source, cond.condition_path)
                        expected = cond.condition_value
                        operator = cond.condition_operator

                        try:
                            val = float(val)
                            expected = float(expected)
                        except:
                            pass

                        result = {
                            "==": val == expected,
                            "!=": val != expected,
                            ">": val > expected,
                            "<": val < expected,
                            "in": expected in str(val),
                            "not_in": expected not in str(val),
                        }.get(operator, False)
                except Exception:
                    result = False

                sub_result = sub_result and result

            group_results.append(sub_result)

        # ✅ Final match: any group passes
        condition_matched = any(group_results) if group_results else True
        if not condition_matched:
            value = rule.default_value

        # ✅ Lookup translation
        if rule.source_lookup and rule.target_lookup:
            try:
                matched_lookup = Lookup.objects.get(parent_lookup=rule.source_lookup, code=value)
                translated = Lookup.objects.filter(
                    parent_lookup=rule.target_lookup, code=matched_lookup.code
                ).first()
                if translated:
                    value = translated
            except Lookup.DoesNotExist:
                pass

        # ✅ Transform function with context
        if rule.transform_function_path:
            transformer = load_function_by_path(rule.transform_function_path)
            try:
                value = transformer(value, context=context)
            except TypeError:
                value = transformer(value)

        was_transformed = True
        setattr(instance, rule.target_field, value)

        execution_log.append({
            "target_field": rule.target_field,
            "json_path": rule.json_path,
            "original_value": original_value,
            "final_value": str(value),
            "condition_matched": condition_matched,
            "transformed": was_transformed,
            "used_default": not condition_matched,
            "expression_used": bool(rule.condition_expression),
            "condition_groups": list(grouped.keys())
        })

    return execution_log



def extract_json_value(data, path_str):
    """
    Dotted path extraction from dict, list, or object.
    Supports paths like "children.0.age" or "user.profile.name".
    """
    keys = path_str.split(".")
    current_val = data
    for k in keys:
        if current_val is None:
            return None
        try:
            if isinstance(current_val, dict):
                current_val = current_val.get(k)
            elif isinstance(current_val, list) and k.isdigit():
                current_val = current_val[int(k)]
            else:
                current_val = getattr(current_val, k, None)
        except Exception:
            return None
    return current_val


def load_function_by_path(path_str):
    """
    Dynamically loads a function from dotted path string.
    Example: 'myapp.plugins.transforms.capitalize'
    """
    import importlib
    module_path, func_name = path_str.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


import time
from case.utils.expression_evaluator import eval_expression, UnsafeExpressionError
from lookup.models import Lookup


def dry_run(case, mapper_target, found_object=None, context=None):
    """
    Simulates processing of the mapper_target without saving to DB.
    Recursively evaluates field rules and nested child MapperTargets.
    Now enhanced with timing, summary, and nested dry-run chaining.
    """
    from case.models import MapperTarget

    field_rules = mapper_target.field_rules.all()
    source = case.case_data
    preview = {}
    context = context or {}
    start_time = time.time()

    summary = {
        "target_id": mapper_target.id,
        "target_name": str(mapper_target),
        "record_count": 0,
        "mapped_fields_count": 0,
        "child_targets_count": 0,
        "execution_time_ms": None,
    }

    try:
        if mapper_target.root_path:
            data_list = extract_json_value(source, mapper_target.root_path)
            if not isinstance(data_list, list):
                return {
                    "target": str(mapper_target),
                    "error": f"root_path '{mapper_target.root_path}' did not return a list"
                }

            filter_func = None
            if mapper_target.filter_function_path:
                filter_func = load_function_by_path(mapper_target.filter_function_path)

            preview_items = []
            for index, item in enumerate(data_list):
                if filter_func:
                    try:
                        if not filter_func(item, case):
                            continue
                    except Exception as e:
                        return {"target": str(mapper_target), "error": f"Filter error @#{index}: {e}"}

                preview_item = {}
                mapped_count = 0

                for rule in field_rules:
                    value = extract_json_value(item, rule.json_path)

                    if rule.condition_expression:
                        try:
                            matched = eval_expression(rule.condition_expression, {**item, **context})
                            if not matched:
                                value = rule.default_value
                        except UnsafeExpressionError:
                            value = rule.default_value

                    elif rule.condition_path and rule.condition_operator:
                        cond_val = extract_json_value(item, rule.condition_path)
                        expected = rule.condition_value
                        operator = rule.condition_operator
                        try:
                            cond_val = float(cond_val)
                            expected = float(expected)
                        except:
                            pass

                        matched = {
                            "==": cond_val == expected,
                            "!=": cond_val != expected,
                            ">": cond_val > expected,
                            "<": cond_val < expected,
                            "in": expected in str(cond_val),
                            "not_in": expected not in str(cond_val),
                        }.get(operator, False)

                        if not matched:
                            value = rule.default_value

                    if rule.source_lookup and rule.target_lookup:
                        try:
                            matched_lookup = Lookup.objects.get(parent_lookup=rule.source_lookup, code=value)
                            translated = Lookup.objects.filter(
                                parent_lookup=rule.target_lookup,
                                code=matched_lookup.code
                            ).first()
                            if translated:
                                value = translated.code
                        except Lookup.DoesNotExist:
                            value = None

                    if rule.transform_function_path:
                        transformer = load_function_by_path(rule.transform_function_path)
                        try:
                            value = transformer(value, context=context)
                        except TypeError:
                            value = transformer(value)

                    preview_item[rule.target_field] = value
                    mapped_count += 1

                summary["mapped_fields_count"] += mapped_count
                summary["record_count"] += 1

                # 🔁 Recurse children
                children = MapperTarget.objects.filter(parent_target=mapper_target)
                child_previews = []
                for child in children:
                    sub = dry_run(case, child, context=item)
                    child_previews.append(sub)
                if child_previews:
                    preview_item["children"] = child_previews
                    summary["child_targets_count"] += len(child_previews)

                preview_items.append(preview_item)

            end_time = time.time()
            summary["execution_time_ms"] = int((end_time - start_time) * 1000)

            return {
                "target": str(mapper_target),
                "action": "dry_run",
                "summary": summary,
                "preview_list": preview_items
            }

        else:
            # 🟢 Flat mapping
            mapped_count = 0
            for rule in field_rules:
                value = extract_json_value(source, rule.json_path)

                if rule.condition_expression:
                    try:
                        matched = eval_expression(rule.condition_expression, {**source, **context})
                        if not matched:
                            value = rule.default_value
                    except UnsafeExpressionError:
                        value = rule.default_value

                elif rule.condition_path and rule.condition_operator:
                    cond_val = extract_json_value(source, rule.condition_path)
                    expected = rule.condition_value
                    operator = rule.condition_operator
                    try:
                        cond_val = float(cond_val)
                        expected = float(expected)
                    except:
                        pass
                    matched = {
                        "==": cond_val == expected,
                        "!=": cond_val != expected,
                        ">": cond_val > expected,
                        "<": cond_val < expected,
                        "in": expected in str(cond_val),
                        "not_in": expected not in str(cond_val),
                    }.get(operator, False)

                    if not matched:
                        value = rule.default_value

                if rule.source_lookup and rule.target_lookup:
                    try:
                        matched_lookup = Lookup.objects.get(parent_lookup=rule.source_lookup, code=value)
                        translated = Lookup.objects.filter(
                            parent_lookup=rule.target_lookup,
                            code=matched_lookup.code
                        ).first()
                        if translated:
                            value = translated.code
                    except Lookup.DoesNotExist:
                        value = None

                if rule.transform_function_path:
                    transformer = load_function_by_path(rule.transform_function_path)
                    try:
                        value = transformer(value, context=context)
                    except TypeError:
                        value = transformer(value)

                preview[rule.target_field] = value
                mapped_count += 1

            summary["record_count"] = 1
            summary["mapped_fields_count"] = mapped_count

            # 🔁 Recurse children
            children = MapperTarget.objects.filter(parent_target=mapper_target)
            child_previews = []
            for child in children:
                sub = dry_run(case=case, mapper_target=child, context=source)
                child_previews.append(sub)

            summary["child_targets_count"] = len(child_previews)
            end_time = time.time()
            summary["execution_time_ms"] = int((end_time - start_time) * 1000)

            return {
                "target": str(mapper_target),
                "action": "dry_run",
                "summary": summary,
                "preview_fields": preview,
                "children": child_previews
            }

    except Exception as e:
        return {
            "target": str(mapper_target),
            "action": "dry_run",
            "error": str(e),
            "summary": summary
        }

def evaluate_conditions(conditions, data_source):
    """
    Evaluates a list of conditions using AND/OR logic.
    """
    results = []
    for condition in conditions:
        actual = extract_json_value(data_source, condition.path)
        expected = condition.value
        operator = condition.operator

        try:
            actual_num = float(actual)
            expected_num = float(expected)
        except (ValueError, TypeError):
            actual_num = actual
            expected_num = expected

        matched = {
            "==": actual_num == expected_num,
            "!=": actual_num != expected_num,
            ">": actual_num > expected_num,
            "<": actual_num < expected_num,
            "in": expected in str(actual_num),
            "not_in": expected not in str(actual_num),
        }.get(operator, False)

        results.append((matched, condition.logic_type))

    # Combine based on logic
    if not results:
        return True

    logic = results[0][1]  # Use logic type from first condition
    matches = [res for res, _ in results]

    return all(matches) if logic == 'AND' else any(matches)

# ✅ Attach dry_run to processor for external access
process_records.dry_run = dry_run
