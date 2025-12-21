"""Component classification engine.

Matches components to types based on configured rules.
"""
from __future__ import annotations
import re
from typing import Optional, List, Dict
from dataclasses import dataclass

from jbom.common.config import get_config, ClassifierConfig


@dataclass
class Rule:
    """Parsed classification rule."""

    field: str
    op: str
    value: str


class ClassificationEngine:
    """Engine for classifying components based on rules."""

    def __init__(self):
        self._classifiers: List[ClassifierConfig] = []
        self._compiled_rules: Dict[str, List[Rule]] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of rules from config."""
        if self._initialized:
            return

        config = get_config()
        self._classifiers = config.component_classifiers
        self._compile_rules()
        self._initialized = True

    def _compile_rules(self):
        """Parse string rules into Rule objects."""
        for classifier in self._classifiers:
            rules = []
            for rule_str in classifier.rules:
                # Parse rule string: "field op value"
                # Example: "lib_id contains resistor"
                parts = rule_str.split(" ", 2)
                if len(parts) >= 3:
                    field_name, op, value = parts
                    rules.append(Rule(field=field_name, op=op, value=value))
                else:
                    # Log warning for invalid rule syntax?
                    pass
            self._compiled_rules[classifier.type] = rules

    def classify(self, lib_id: str, footprint: str) -> Optional[str]:
        """Classify a component based on its library ID and footprint.

        Args:
            lib_id: Component library identifier
            footprint: Component footprint name

        Returns:
            Component type string (e.g., "RES", "LED") or None if no match.
        """
        self._ensure_initialized()

        # Context for rule evaluation
        context = {
            "lib_id": lib_id.lower(),
            "footprint": footprint.lower(),
        }

        # Iterate through classifiers in order
        for classifier in self._classifiers:
            # Check if ANY rule matches (OR logic)
            # If rules list is empty, it never matches
            rules = self._compiled_rules.get(classifier.type, [])
            for rule in rules:
                if self._evaluate_rule(rule, context):
                    return classifier.type

        return None

    def _evaluate_rule(self, rule: Rule, context: Dict[str, str]) -> bool:
        """Evaluate a single rule against the context."""
        # Get field value from context
        # Handle derived fields like 'lib_id_suffix' if needed, or just standard ones
        subject = context.get(rule.field, "")
        # subject is already lowercased in context
        target = rule.value.lower()  # Rules are case-insensitive by default

        if rule.op == "contains":
            return target in subject
        elif rule.op == "startswith":
            return subject.startswith(target)
        elif rule.op == "endswith":
            return subject.endswith(target)
        elif rule.op == "eq":
            return subject == target
        elif rule.op == "matches":
            try:
                return bool(re.search(target, subject))
            except re.error:
                return False

        return False


# Global engine instance
_engine: Optional[ClassificationEngine] = None


def get_engine() -> ClassificationEngine:
    """Get the global classification engine instance."""
    global _engine
    if _engine is None:
        _engine = ClassificationEngine()
    return _engine


def reload_engine() -> ClassificationEngine:
    """Reload the global classification engine instance (clearing cache)."""
    global _engine
    _engine = None
    return get_engine()
