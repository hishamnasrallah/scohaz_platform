# case/utils/expression_evaluator.py

import ast
import operator

SAFE_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
    ast.And: all,         # Supports multiple values
    ast.Or: any,
}

ALLOWED_NAMES = {"True": True, "False": False, "None": None}

class UnsafeExpressionError(Exception):
    pass

def eval_expression(expression: str, variables: dict) -> bool:
    """
    Safely evaluates a logical expression using predefined variables.

    Example:
        expr = "income > 10000 and age < 30"
        vars = {"income": 15000, "age": 25}
        result = eval_expression(expr, vars)  # True
    """
    try:
        tree = ast.parse(expression, mode='eval')
        return _eval_ast(tree.body, variables)
    except Exception as e:
        raise UnsafeExpressionError(f"Invalid expression: {expression}. Error: {e}")

def _eval_ast(node, variables):
    if isinstance(node, ast.BoolOp):
        values = [_eval_ast(value, variables) for value in node.values]
        op_func = SAFE_OPERATORS.get(type(node.op))
        if not op_func:
            raise UnsafeExpressionError(f"Unsupported boolean operator: {ast.dump(node.op)}")
        return op_func(values)

    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_ast(node.operand, variables)

    elif isinstance(node, ast.Compare):
        left = _eval_ast(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_ast(comparator, variables)
            op_func = SAFE_OPERATORS.get(type(op))
            if not op_func:
                raise UnsafeExpressionError(f"Unsupported comparison: {ast.dump(op)}")
            if not op_func(left, right):
                return False
        return True

    elif isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in ALLOWED_NAMES:
            return ALLOWED_NAMES[node.id]
        raise UnsafeExpressionError(f"Access to unknown variable '{node.id}'.")

    elif isinstance(node, ast.Constant):  # Python 3.8+
        return node.value

    elif isinstance(node, ast.Str):  # Python < 3.8
        return node.s

    elif isinstance(node, ast.Num):  # Python < 3.8
        return node.n

    else:
        raise UnsafeExpressionError(f"Unsupported node: {ast.dump(node)}")
