from copy import deepcopy
from typing import Any


CUSTOMER_LEDGER_SCHEMA_REGISTRY: dict[str, dict[str, Any]] = {
    "CUSTOMER_CONTRACT_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "item_type": {"type": "string", "enum": ["PRODUCT", "SERVICE"]},
                "product_id": {"type": ["string", "null"]},
                "service_name": {"type": ["string", "null"]},
                "introduction_status": {
                    "type": "string",
                    "enum": ["NONE", "PLANNED", "ACTIVE", "EXPIRED", "TERMINATED"],
                },
                "introduction_start_date": {"type": ["string", "null"]},
                "introduction_end_date": {"type": ["string", "null"]},
                "maintenance_status": {
                    "type": "string",
                    "enum": ["NONE", "PLANNED", "ACTIVE", "EXPIRED", "TERMINATED"],
                },
                "maintenance_start_date": {"type": ["string", "null"]},
                "maintenance_end_date": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
            },
            "required": ["item_type"],
            "additionalProperties": False,
        },
    },
    "CUSTOMER_SERVICE_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string"},
                "introduction_status": {
                    "type": "string",
                    "enum": ["NONE", "PLANNED", "ACTIVE", "EXPIRED", "TERMINATED"],
                },
                "introduction_start_date": {"type": ["string", "null"]},
                "introduction_end_date": {"type": ["string", "null"]},
                "maintenance_status": {
                    "type": "string",
                    "enum": ["NONE", "PLANNED", "ACTIVE", "EXPIRED", "TERMINATED"],
                },
                "maintenance_start_date": {"type": ["string", "null"]},
                "maintenance_end_date": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
            },
            "required": ["service_name"],
            "additionalProperties": False,
        },
    },
    "CUSTOMER_VPN_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "vpn_type": {
                    "type": "string",
                    "enum": ["IPSEC", "SSL", "MPLS", "OTHER"],
                },
                "provider_name": {"type": ["string", "null"]},
                "status": {
                    "type": "string",
                    "enum": ["PLANNED", "ACTIVE", "RETIRED"],
                },
                "notes": {"type": ["string", "null"]},
            },
            "required": ["name", "vpn_type"],
            "additionalProperties": False,
        },
    },
    "CUSTOMER_ENVIRONMENT_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "environment_type": {
                    "type": "string",
                    "enum": ["PRODUCTION", "VERIFICATION", "INTERNAL", "OTHER"],
                },
                "status": {
                    "type": "string",
                    "enum": ["PLANNED", "ACTIVE", "RETIRED"],
                },
                "product_code": {"type": ["string", "null"]},
                "product_version": {"type": ["string", "null"]},
                "notes": {"type": ["string", "null"]},
            },
            "required": ["name", "environment_type"],
            "additionalProperties": False,
        },
    },
    "CUSTOMER_CUSTOMIZATION_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "category": {"type": ["string", "null"]},
                "summary": {"type": "string"},
                "business_purpose": {"type": ["string", "null"]},
                "affected_components": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "status": {
                    "type": "string",
                    "enum": ["PLANNED", "ACTIVE", "RETIRED", "UNKNOWN"],
                },
                "notes": {"type": ["string", "null"]},
            },
            "required": ["name", "summary", "affected_components", "status"],
            "additionalProperties": False,
        },
    },
    "CUSTOMER_REPOSITORY_V1": {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "properties": {
                "repository_type": {"type": "string"},
                "name": {"type": ["string", "null"]},
                "purpose": {"type": ["string", "null"]},
            },
            "required": ["repository_type"],
            "additionalProperties": False,
        },
    },
}


def customer_ledger_schema_registry() -> dict[str, dict[str, Any]]:
    return deepcopy(CUSTOMER_LEDGER_SCHEMA_REGISTRY)


def value_matches_schema(value: Any, schema: dict[str, Any]) -> bool:
    expected = schema.get("type")
    allowed_types = expected if isinstance(expected, list) else [expected]
    if value is None:
        return "null" in allowed_types
    if "array" in allowed_types:
        return (
            isinstance(value, list)
            and len(value) >= int(schema.get("minItems", 0))
            and all(
                value_matches_schema(item, schema.get("items", {})) for item in value
            )
        )
    if "object" in allowed_types:
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if any(name not in value for name in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(
            name not in properties for name in value
        ):
            return False
        return all(
            name not in value or value_matches_schema(value[name], child_schema)
            for name, child_schema in properties.items()
        )
    if "string" in allowed_types and not isinstance(value, str):
        return False
    if "number" in allowed_types and (
        not isinstance(value, (int, float)) or isinstance(value, bool)
    ):
        return False
    if "integer" in allowed_types and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        return False
    if "boolean" in allowed_types and not isinstance(value, bool):
        return False
    allowed_values = schema.get("enum")
    return allowed_values is None or value in allowed_values
