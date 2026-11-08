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
