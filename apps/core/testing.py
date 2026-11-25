"""Test-only shim: Django 5.0's Context.__copy__ breaks on Python 3.14, which crashes the test client
whenever a template renders.  Importing this module patches it; it is a no-op on older Pythons."""
import sys

from django.template.context import BaseContext

if sys.version_info >= (3, 14):
    def _copy(self):
        dup = object.__new__(self.__class__)
        dup.__dict__.update(self.__dict__)
        dup.dicts = self.dicts[:]
        return dup

    BaseContext.__copy__ = _copy


# Tests written for the per-level prices pin the date switch far ahead, so they keep testing the legacy pricing
# after the all-access plan goes live (settings.SINGLE_PLAN_START).  New-plan tests live in payments/tests.py.
import datetime as _dt  # noqa: E402

from django.test import override_settings as _override  # noqa: E402

LEGACY_PRICING = dict(SINGLE_PLAN_START=_dt.date(2099, 1, 1))
legacy_pricing = _override(**LEGACY_PRICING)
