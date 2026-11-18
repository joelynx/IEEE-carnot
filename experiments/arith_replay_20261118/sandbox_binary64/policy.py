"""AST whitelist and exact-arithmetic rewrite for generated programs (PLAN.md §3.3).

check_and_transform(source) -> code object, or raises PolicyError.

Rejected: imports outside ALLOWED_MODULES, class definitions, async code,
global/nonlocal, ``with`` blocks, any attribute beginning with "_", any name
beginning with "__", and introspection/escape builtins (eval, exec, open, ...).

Rewritten: float literals -> Q("literal") (exact); + - * / // % ** (also the
augmented forms) -> _bin(op, a, b), so int/int is an exact Fraction and
Fraction/Decimal mixes coerce instead of raising.
"""

from __future__ import annotations

import ast
import copy

ALLOWED_MODULES = {"math", "fractions", "decimal", "finq", "itertools", "functools"}
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "input", "globals", "locals", "vars", "getattr",
    "setattr", "delattr", "breakpoint", "exit", "quit", "help", "memoryview", "object",
    "type", "super", "classmethod", "staticmethod", "property", "dir", "id", "__import__",
}
FORBIDDEN_NODES = (
    ast.ClassDef, ast.AsyncFunctionDef, ast.AsyncFor, ast.AsyncWith, ast.Await,
    ast.Global, ast.Nonlocal, ast.With,
)
ARITH = {
    ast.Add: "Add", ast.Sub: "Sub", ast.Mult: "Mult", ast.Div: "Div",
    ast.FloorDiv: "FloorDiv", ast.Mod: "Mod", ast.Pow: "Pow",
}


class PolicyError(ValueError):
    pass


def _check(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise PolicyError(f"line {getattr(node, 'lineno', '?')}: {type(node).__name__} is not allowed")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_MODULES:
                    raise PolicyError(f"line {node.lineno}: import of {alias.name!r} is not allowed")
        if isinstance(node, ast.ImportFrom):
            if node.level or (node.module or "").split(".")[0] not in ALLOWED_MODULES:
                raise PolicyError(f"line {node.lineno}: import from {node.module!r} is not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise PolicyError(f"line {node.lineno}: private attribute {node.attr!r} is not allowed")
        if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in FORBIDDEN_NAMES):
            raise PolicyError(f"line {node.lineno}: name {node.id!r} is not allowed")
        if isinstance(node, ast.Constant) and isinstance(node.value, complex):
            raise PolicyError(f"line {node.lineno}: complex numbers are not allowed")
    if not any(isinstance(n, ast.FunctionDef) and n.name == "solve" for n in tree.body):
        raise PolicyError("the program must define a top-level function solve()")


class _Rewrite(ast.NodeTransformer):
    def __init__(self, source: str) -> None:
        self.source = source

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if isinstance(node.value, float):
            text = ast.get_source_segment(self.source, node) or repr(node.value)
            call = ast.Call(ast.Name("Q", ast.Load()), [ast.Constant(text.replace("_", ""))], [])
            return ast.copy_location(call, node)
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        op = ARITH.get(type(node.op))
        if op is None:
            return node
        call = ast.Call(ast.Name("_bin", ast.Load()), [ast.Constant(op), node.left, node.right], [])
        return ast.copy_location(call, node)

    def visit_AugAssign(self, node: ast.AugAssign) -> ast.AST:
        self.generic_visit(node)
        op = ARITH.get(type(node.op))
        if op is None:
            return node
        load_target = copy.deepcopy(node.target)
        for sub in ast.walk(load_target):
            if hasattr(sub, "ctx"):
                sub.ctx = ast.Load()
        call = ast.Call(ast.Name("_bin", ast.Load()), [ast.Constant(op), load_target, node.value], [])
        return ast.copy_location(ast.Assign([node.target], call), node)


def check_and_transform(source: str):
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise PolicyError(f"syntax error: {exc.msg} (line {exc.lineno})") from exc
    _check(tree)
    tree = ast.fix_missing_locations(_Rewrite(source).visit(tree))
    return compile(tree, "<program>", "exec")
