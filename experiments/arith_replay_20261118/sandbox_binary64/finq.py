"""Binary64 twin of carnot/sandbox/finq.py (arithmetic replay, 18 November 2026).

Same names as the exact module, but every non-integer number is a Python float
(IEEE 754 binary64), as in a program-of-thought pipeline without the exact
layer.  policy.py is unchanged: it still rewrites operators to ``_bin`` and
float literals to ``Q("literal")``.  With the definitions below that is the
same as running the program text in plain Python with ``Q = float``:

* ``Q(x)`` is ``float(x)``; integer literals stay ``int``; ``/`` is true division;
* ``round_half_up`` rounds the shortest round-trip decimal of the float half-up
  (the careful choice; no binary tie artefacts);
* roots, logs and exponentials come from ``math``.

This module is copied into the sandbox and has no dependencies beyond stdlib.
"""

from __future__ import annotations

import decimal as _decimal
import math as _math
import operator

_OPS = {
    "Add": operator.add,
    "Sub": operator.sub,
    "Mult": operator.mul,
    "Div": operator.truediv,
    "FloorDiv": operator.floordiv,
    "Mod": operator.mod,
}


def _is_number(value) -> bool:
    return isinstance(value, (int, float))  # bool is an int


def Q(value, denominator=None):
    """Number constructor of the binary64 twin: Q("0.05"), Q(3), Q(1, 3) are floats."""

    if denominator is not None:
        return _bin("Div", Q(value), Q(denominator))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.replace("_", "").replace(",", "").strip()
        if "/" in text:
            numerator, divisor = text.split("/", 1)
            return float(numerator) / float(divisor)
        return float(text)
    raise TypeError(f"cannot make a number from {type(value).__name__}")


Fraction = Q


def Decimal(value=0):
    return Q(value)


def _pow(base, exponent):
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        return base**exponent
    return _math.pow(base, exponent)


def _bin(op, left, right):
    if op == "Pow":
        if _is_number(left) and _is_number(right):
            return _pow(left, right)
        return left**right
    return _OPS[op](left, right)


def _sum(iterable, start=0):
    return sum(iterable, start)


def _prod(iterable, start=1):
    return _math.prod(iterable, start=start)


def round_half_up(value, places=0):
    """Half-up rounding (ties away from zero) of the float's shortest round-trip decimal."""

    places = int(places)
    exact = _decimal.Decimal(value) if isinstance(value, int) else _decimal.Decimal(repr(float(value)))
    with _decimal.localcontext() as context:
        context.prec = 400
        quantised = exact.quantize(_decimal.Decimal(1).scaleb(-places), rounding=_decimal.ROUND_HALF_UP)
    return float(quantised)


def sqrt(value):
    return _math.sqrt(value)


def exp(value):
    return _math.exp(value)


def ln(value):
    return _math.log(value)


def log(value, base=None):
    if base is None:
        return _math.log(value)
    return _math.log(value) / _math.log(base)


def log10(value):
    return _math.log10(value)


def log2(value):
    return _math.log2(value)


PI = _math.pi
E = _math.e


def erf(value):
    return _math.erf(value)


def norm_cdf(value):
    """Standard normal cumulative distribution function N(x)."""

    return (1.0 + _math.erf(float(value) / _math.sqrt(2.0))) / 2.0


def norm_pdf(value):
    x = float(value)
    return _math.exp(-(x * x) / 2.0) / _math.sqrt(2.0 * _math.pi)


def solve(function, low, high, tolerance=None, max_iterations=500):
    """Root of ``function`` on [low, high] by bisection (requires a sign change)."""

    low_v, high_v = float(low), float(high)
    f_low, f_high = function(low_v), function(high_v)
    if f_low == 0:
        return low_v
    if f_high == 0:
        return high_v
    if (f_low > 0) == (f_high > 0):
        raise ValueError("solve(): no sign change on the bracket [low, high]")
    tolerance = 1e-12 if tolerance is None else float(tolerance)
    for _ in range(max_iterations):
        mid = (low_v + high_v) / 2
        f_mid = function(mid)
        if f_mid == 0 or (high_v - low_v) / 2 < tolerance:
            return mid
        if (f_mid > 0) == (f_low > 0):
            low_v, f_low = mid, f_mid
        else:
            high_v = mid
    return (low_v + high_v) / 2


math = _math

__all__ = [
    "Q", "Fraction", "Decimal", "sqrt", "exp", "ln", "log", "log10", "log2", "erf",
    "norm_cdf", "norm_pdf", "solve", "round_half_up", "PI", "E",
]
