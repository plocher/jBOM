"""Supplier-specific search provider implementations.

Each sub-package corresponds to one supplier and contains:
- provider.py  — SearchProvider implementation
- api.py       — Raw HTTP/DB client (if applicable)
- query_planner.py — Category-aware parametric query builder (if applicable)

The supplier configuration schemas and YAML profiles live in
``jbom.config.suppliers``; this package owns the Python implementations.
"""
