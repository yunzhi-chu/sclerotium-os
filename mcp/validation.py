"""MCP Tool Schema Validation — Pydantic runtime parameter validation.

Validates tool call arguments against their JSON Schema definitions
before execution. Catches type mismatches, missing required fields,
and value constraint violations early.

Usage:
    validator = ToolSchemaValidator()
    errors = validator.validate("file_read", {"file_path": 123})
    # → ["file_path: expected string, got int"]
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("sclerotium.validation")


class ToolSchemaValidator:
    """Validate tool call arguments against JSON Schema definitions."""

    # JSON Schema type → Python type mapping for error messages
    _TYPE_MAP: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, parameters: dict[str, Any]) -> None:
        """Register a tool's JSON Schema for validation."""
        self._schemas[name] = parameters

    def register_from_registry(self, registry: Any) -> None:
        """Register all tools from a ToolRegistry."""
        for tool_def in registry.list_tools():
            self._schemas[tool_def["name"]] = tool_def.get("parameters", {})

    def validate(
        self, tool_name: str, args: dict[str, Any],
    ) -> list[str]:
        """Validate tool arguments against schema. Returns list of error messages.

        Returns empty list if all arguments are valid.
        """
        schema = self._schemas.get(tool_name)
        if schema is None:
            return []  # Unknown tool — let execution handle it

        errors: list[str] = []
        properties = schema.get("properties", {})
        required: list[str] = schema.get("required", [])

        # Check required fields
        for field in required:
            if field not in args or args[field] is None:
                errors.append(f"{tool_name}: missing required field '{field}'")

        # Validate each argument
        for key, value in args.items():
            if value is None:
                continue

            prop_schema = properties.get(key, {})
            if not prop_schema:
                continue  # Unknown field — pass through (LLM might hallucinate extras)

            prop_type = prop_schema.get("type", "")
            field_errors = self._validate_field(tool_name, key, value, prop_schema)
            errors.extend(field_errors)

        return errors

    def _validate_field(
        self, tool_name: str, field: str, value: Any, schema: dict[str, Any],
    ) -> list[str]:
        """Validate a single field value against its schema."""
        errors: list[str] = []
        expected_type = schema.get("type", "")

        if not expected_type:
            return errors

        # Type checking
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{tool_name}.{field}: expected string, got {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            if isinstance(value, float) and value == int(value):
                pass  # Accept float that's really an int
            else:
                errors.append(f"{tool_name}.{field}: expected integer, got {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            errors.append(f"{tool_name}.{field}: expected number, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            errors.append(f"{tool_name}.{field}: expected boolean, got {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            errors.append(f"{tool_name}.{field}: expected array, got {type(value).__name__}")
        elif expected_type == "object" and not isinstance(value, dict):
            errors.append(f"{tool_name}.{field}: expected object, got {type(value).__name__}")

        # Enum constraint
        enum_values = schema.get("enum")
        if enum_values and value not in enum_values:
            errors.append(
                f"{tool_name}.{field}: '{value}' not in allowed values: {enum_values}"
            )

        # String constraints
        if expected_type == "string" and isinstance(value, str):
            max_len = schema.get("maxLength")
            if max_len and len(value) > max_len:
                errors.append(
                    f"{tool_name}.{field}: string too long ({len(value)} > {max_len})"
                )

        # Numeric constraints
        if expected_type in ("integer", "number") and isinstance(value, (int, float)):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")
            if minimum is not None and value < minimum:
                errors.append(f"{tool_name}.{field}: {value} < minimum {minimum}")
            if maximum is not None and value > maximum:
                errors.append(f"{tool_name}.{field}: {value} > maximum {maximum}")

        # Array constraints
        if expected_type == "array" and isinstance(value, list):
            max_items = schema.get("maxItems")
            if max_items and len(value) > max_items:
                errors.append(
                    f"{tool_name}.{field}: too many items ({len(value)} > {max_items})"
                )

        return errors

    def is_valid(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Quick check: are the arguments valid?"""
        return len(self.validate(tool_name, args)) == 0

    def get_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get the JSON Schema for a tool."""
        return self._schemas.get(tool_name)

    @property
    def schema_count(self) -> int:
        return len(self._schemas)
