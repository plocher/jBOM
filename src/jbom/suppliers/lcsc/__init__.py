"""LCSC / JLCPCB supplier implementation.

Modules
-------
api            — JlcpcbPartsApi: raw HTTP client for the JLCPCB parts API
provider       — JlcpcbProvider: SearchProvider backed by the live API
query_planner  — Parametric query plan builder (RES / CAP / IND / CON)
pricing        — Bulk-break unit price selection for optional BOM cost
"""
