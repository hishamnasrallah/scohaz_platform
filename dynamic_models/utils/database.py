from django.db import connection

def is_sqlite():
    """
    Check if the current database backend is SQLite.
    """
    return connection.vendor == 'sqlite'

def disable_foreign_keys():
    """
    Disable foreign key checks for SQLite.
    """
    if is_sqlite():
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF;")

def enable_foreign_keys():
    """
    Enable foreign key checks for SQLite.
    """
    if is_sqlite():
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON;")
