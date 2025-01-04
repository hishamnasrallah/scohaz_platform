from django.db import transaction

class SchemaChangeManager:
    _changes = []

    @classmethod
    def add_change(cls, func, *args, **kwargs):
        cls._changes.append((func, args, kwargs))
        transaction.on_commit(cls.execute_changes)

    @classmethod
    def execute_changes(cls):
        while cls._changes:
            func, args, kwargs = cls._changes.pop(0)
            func(*args, **kwargs)
