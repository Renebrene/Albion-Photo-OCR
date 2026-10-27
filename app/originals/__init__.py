"""Availability of the registered original files.

The technical section ("Данные" → "Доступность оригиналов") shows a summary per
configured root straight from the database; the full per-file walk is a job
(ORIGINALS_CHECK), because 57 000 stat() calls do not belong in a request.
"""
