"""Exact-arithmetic helpers available to generated programs (PLAN.md §3.3).

Every arithmetic operator in a generated program is rewritten to ``_bin`` /
``_pow`` (see policy.py), and every float literal to ``Q("literal")``, so:

* rational arithmetic is exact (``fractions.Fraction``);
* irrational or iterative operations (roots, logs, exponentials, the normal
  CDF, root-finding) use ``decimal`` at high precision and return ``Decimal``,
  which the harness treats as inexact (allowed only in half-up fields);
* mixing Fraction and Decimal coerces to Decimal instead of raising.

This module is copied into the sandbox and has no dependencies beyond stdlib.
"""

from __future__ import annotations

import decimal
import math as _math
import operator
from decimal import Decimal, localcontext
from fractions import Fraction

PRECISION = 60
INEXACT_DECIMAL_DIGITS = 50
decimal.getcontext().prec = PRECISION

_OPS = {
    "Add": operator.add,
    "Sub": operator.sub,
    "Mult": operator.mul,
    "Div": operator.truediv,
    "FloorDiv": operator.floordiv,
    "Mod": operator.mod,
}


def _is_rational(value) -> bool:
    return isinstance(value, (int, Fraction))  # bool is an int


def _is_number(value) -> bool:
    return isinstance(value, (int, Fraction, Decimal, float))


def _dec(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    value = Fraction(value)
    return Decimal(value.numerator) / Decimal(value.denominator)


def Q(value, denominator=None):
    """Exact number constructor: Q("0.05"), Q(3), Q(1, 3)."""

    if denominator is not None:
        return _bin("Div", Q(value), Q(denominator))
    if isinstance(value, bool):
        return Fraction(int(value))
    if _is_rational(value):
        return Fraction(value)
    if isinstance(value, Decimal):
        digits = "".join(map(str, value.as_tuple().digits)).lstrip("0")
        return Fraction(value) if value.is_finite() and len(digits) < INEXACT_DECIMAL_DIGITS else value
    if isinstance(value, float):
        return Fraction(repr(value))
    if isinstance(value, str):
        return Fraction(value.replace("_", "").replace(",", "").strip())
    raise TypeError(f"cannot make an exact number from {type(value).__name__}")


def _integer_root(n: int, k: int) -> int | None:
    if n < 0:
        if k % 2 == 0:
            return None
        root = _integer_root(-n, k)
        return None if root is None else -root
    if n in (0, 1):
        return n
    low, high = 0, 1 << ((n.bit_length() + k - 1) // k + 1)
    while low < high:
        mid = (low + high) // 2
        if mid**k < n:
            low = mid + 1
        else:
            high = mid
    return low if low**k == n else None


def _pow(base, exponent):
    if _is_rational(exponent) and Fraction(exponent).denominator == 1:
        power = int(exponent)
        if _is_rational(base):
            return Fraction(base) ** power
        return _dec(base) ** power
    if _is_rational(base) and _is_rational(exponent):
        base_q, exp_q = Fraction(base), Fraction(exponent)
        numerator = _integer_root(base_q.numerator, exp_q.denominator)
        denominator = _integer_root(base_q.denominator, exp_q.denominator)
        if numerator is not None and denominator is not None:
            return Fraction(numerator, denominator) ** exp_q.numerator
    base_d, exp_d = _dec(base), _dec(exponent)
    if base_d < 0:
        raise ValueError("non-integer power of a negative number")
    if base_d == 0:
        return Fraction(0) if exp_d > 0 else _dec(base) ** exp_d
    return base_d**exp_d


def _bin(op, left, right):
    if op == "Pow":
        if _is_number(left) and _is_number(right):
            return _pow(left, right)
        return left**right
    if _is_number(left) and _is_number(right):
        if isinstance(left, (Decimal, float)) or isinstance(right, (Decimal, float)):
            return _OPS[op](_dec(left), _dec(right))
        if op == "Div":
            return Fraction(left) / Fraction(right)
    return _OPS[op](left, right)


def _sum(iterable, start=0):
    total = start
    for item in iterable:
        total = _bin("Add", total, item)
    return total


def _prod(iterable, start=1):
    total = start
    for item in iterable:
        total = _bin("Mult", total, item)
    return total


def round_half_up(value, places=0):
    """Half-up rounding (ties away from zero), returned as an exact Fraction."""

    places = int(places)
    if _is_rational(value):
        scaled = Fraction(value) * Fraction(10) ** places
        magnitude = _math.floor(abs(scaled) + Fraction(1, 2))
        return Fraction(magnitude if scaled >= 0 else -magnitude) / Fraction(10) ** places
    quantised = _dec(value).quantize(Decimal(1).scaleb(-places), rounding=decimal.ROUND_HALF_UP)
    return Fraction(quantised)


def sqrt(value):
    if _bin("Sub", value, 0) < 0:
        raise ValueError("square root of a negative number")
    return _pow(value, Fraction(1, 2))


def exp(value):
    if _is_rational(value) and value == 0:
        return Fraction(1)
    return _dec(value).exp()


def ln(value):
    if _is_rational(value) and value == 1:
        return Fraction(0)
    if _dec(value) <= 0:
        raise ValueError("logarithm of a non-positive number")
    return _dec(value).ln()


def log(value, base=None):
    if base is None:
        return ln(value)
    return _bin("Div", ln(value), ln(base))


def log10(value):
    return log(value, 10)


def log2(value):
    return log(value, 2)


def _pi() -> Decimal:
    with localcontext() as context:
        context.prec = PRECISION + 10
        # Machin's formula; stop once terms fall below the working precision
        # (looping until a term underflows to exactly zero takes ~700k iterations).
        epsilon = Decimal(10) ** -(context.prec + 5)

        def arctan_inv(x: int) -> Decimal:
            total, term, n, sign = Decimal(0), Decimal(1) / x, 1, 1
            x2 = x * x
            while term > epsilon:
                total += sign * term / n
                term /= x2
                n += 2
                sign = -sign
            return total

        value = 4 * (4 * arctan_inv(5) - arctan_inv(239))
    return +value


PI = _pi()
E = Decimal(1).exp()


def erf(value):
    x = _dec(value)
    with localcontext() as context:
        context.prec = PRECISION + 40
        if abs(x) > 9:
            return Decimal(1) if x > 0 else Decimal(-1)
        total, term, n = Decimal(0), x, 0
        x2 = x * x
        while True:
            contribution = term / (2 * n + 1)
            total += contribution
            if abs(contribution) < Decimal(10) ** (-(PRECISION + 20)):
                break
            n += 1
            term = -term * x2 / n
        result = 2 / _pi_high(context.prec).sqrt() * total
    return +result


def _pi_high(prec: int) -> Decimal:
    return PI if prec <= PRECISION + 10 else _pi()


def norm_cdf(value):
    """Standard normal cumulative distribution function N(x)."""

    x = _dec(value)
    return (1 + erf(x / Decimal(2).sqrt())) / 2


def norm_pdf(value):
    x = _dec(value)
    return (-(x * x) / 2).exp() / (2 * PI).sqrt()


def solve(function, low, high, tolerance=None, max_iterations=500):
    """Root of ``function`` on [low, high] by bisection (requires a sign change)."""

    low_v, high_v = _dec(low), _dec(high)
    f_low, f_high = _dec(function(Q(low))), _dec(function(Q(high)))
    if f_low == 0:
        return Q(low)
    if f_high == 0:
        return Q(high)
    if (f_low > 0) == (f_high > 0):
        raise ValueError("solve(): no sign change on the bracket [low, high]")
    tolerance = Decimal(10) ** -45 if tolerance is None else _dec(tolerance)
    for _ in range(max_iterations):
        mid = (low_v + high_v) / 2
        f_mid = _dec(function(mid))
        if f_mid == 0 or (high_v - low_v) / 2 < tolerance:
            return mid
        if (f_mid > 0) == (f_low > 0):
            low_v, f_low = mid, f_mid
        else:
            high_v = mid
    return (low_v + high_v) / 2


def _no_float(*_args, **_kwargs):
    raise TypeError("float() is not allowed; keep values exact (use Q(...) or Fraction)")


class _MathShim:
    """``math`` replacement: exact where possible, high-precision Decimal otherwise."""

    pi = PI
    e = E
    inf = Decimal("Infinity")
    sqrt = staticmethod(sqrt)
    exp = staticmethod(exp)
    log = staticmethod(log)
    log10 = staticmethod(log10)
    log2 = staticmethod(log2)
    erf = staticmethod(erf)
    pow = staticmethod(_pow)
    prod = staticmethod(_prod)
    fsum = staticmethod(_sum)
    floor = staticmethod(_math.floor)
    ceil = staticmethod(_math.ceil)
    trunc = staticmethod(_math.trunc)
    factorial = staticmethod(_math.factorial)
    comb = staticmethod(_math.comb)
    perm = staticmethod(_math.perm)
    gcd = staticmethod(_math.gcd)
    lcm = staticmethod(_math.lcm)
    isqrt = staticmethod(_math.isqrt)

    @staticmethod
    def fabs(value):
        return abs(value)

    @staticmethod
    def isclose(a, b, rel_tol=Fraction(1, 10**9), abs_tol=0):
        difference = abs(_bin("Sub", a, b))
        return difference <= max(_bin("Mult", rel_tol, max(abs(a), abs(b))), abs_tol)


math = _MathShim()

__all__ = [
    "Q", "Fraction", "Decimal", "sqrt", "exp", "ln", "log", "log10", "log2", "erf",
    "norm_cdf", "norm_pdf", "solve", "round_half_up", "PI", "E",
]
