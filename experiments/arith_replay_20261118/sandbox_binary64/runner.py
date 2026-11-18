"""Execute ONE generated program in binary64 and print its typed result as one JSON line.

Twin of carnot/sandbox/runner.py for the arithmetic replay (18 November 2026).  The
differences from the exact runner are confined to what the program can see: the names
``Q``, ``Fraction``, ``Decimal`` and ``math`` come from the binary64 finq.py in this
folder, ``round`` is its half-up rounding, ``sum`` and ``float`` are the built-ins.
The policy check, the result protocol and the encoding are the same.

Run as a child process (by worker.py) with resource limits; reads
{"code": "..."} from stdin.  Never imported by the host pipeline.
"""

from __future__ import annotations

import builtins
import functools
import itertools
import json
import os
import sys
import traceback
import types
from decimal import Decimal
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import finq  # noqa: E402
from policy import PolicyError, check_and_transform  # noqa: E402

MODULES = {"math": finq.math, "fractions": types.SimpleNamespace(Fraction=finq.Fraction),
           "decimal": types.SimpleNamespace(Decimal=finq.Decimal), "finq": finq,
           "itertools": itertools, "functools": functools}


def _import(name, globals_=None, locals_=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if level or root not in MODULES:
        raise ImportError(f"import of {name!r} is not allowed")
    return MODULES[root]


def _round(value, ndigits=None):
    result = finq.round_half_up(value, 0 if ndigits is None else ndigits)
    return int(result) if ndigits is None else result


SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in (
        "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "int", "isinstance",
        "len", "list", "map", "max", "min", "range", "reversed", "set", "sorted", "str", "tuple",
        "zip", "ValueError", "ZeroDivisionError", "ArithmeticError", "Exception", "TypeError",
        "KeyError", "IndexError", "StopIteration", "True", "False", "None", "frozenset", "next",
        "iter", "repr", "format", "hasattr",
    )
    if hasattr(builtins, name)
}
SAFE_BUILTINS.update(
    __import__=_import, round=_round, sum=finq._sum, pow=lambda a, b, m=None: finq._bin("Pow", a, b),
    float=float, print=lambda *a, **k: None,
)


def encode(value):
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "frac", "n": str(value), "d": "1"}
    if isinstance(value, Fraction):
        return {"t": "frac", "n": str(value.numerator), "d": str(value.denominator)}
    if isinstance(value, Decimal):
        if not value.is_finite():
            return {"t": "invalid", "v": str(value)}
        return {"t": "dec", "v": str(value)}
    if isinstance(value, float):
        return {"t": "float", "v": repr(value)}
    if isinstance(value, str):
        return {"t": "str", "v": value[:200]}
    return {"t": "invalid", "v": repr(value)[:200]}


def main() -> None:
    request = json.loads(sys.stdin.read())
    try:
        code = check_and_transform(request["code"])
    except PolicyError as exc:
        print(json.dumps({"ok": False, "stage": "policy", "error": str(exc)}))
        return
    namespace = {"__builtins__": SAFE_BUILTINS, "__name__": "program", "Q": finq.Q, "Fraction": finq.Fraction,
                 "Decimal": finq.Decimal, "math": finq.math, "_bin": finq._bin, "_pow": finq._pow}
    for name in finq.__all__:
        namespace.setdefault(name, getattr(finq, name))
    try:
        exec(code, namespace)  # noqa: S102 - policy-checked, resource-limited child process
        result = namespace["solve"]()
    except Exception as exc:  # noqa: BLE001
        frames = [f for f in traceback.extract_tb(exc.__traceback__) if f.filename == "<program>"]
        where = f" (line {frames[-1].lineno})" if frames else ""
        print(json.dumps({"ok": False, "stage": "runtime", "error": f"{type(exc).__name__}: {exc}{where}"[:500]}))
        return
    if not isinstance(result, dict) or not all(isinstance(k, str) for k in result):
        print(json.dumps({"ok": False, "stage": "result", "error": "solve() must return a dict with string keys"}))
        return
    print(json.dumps({"ok": True, "values": {k: encode(v) for k, v in result.items()}}))


if __name__ == "__main__":
    main()
