"""Backup and restore of the working installation.

The technical section ("Данные" → "Бэкапы") talks to this package through the
job queue: a backup of a 52 MB database dump and a data archive takes
seconds, and a restore must never block an HTTP request.
"""
