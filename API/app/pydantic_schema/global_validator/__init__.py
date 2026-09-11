import json
from typing import TypeVar, Type
from typing import Union, List, Any
from pydantic import BaseModel, ValidationError, create_model, field_validator, model_validator
from pydantic.fields import FieldInfo

# Mapeo de tipos del schema declarativo a tipos Python
TYPE_MAP = {
    "string": str,
    "number": float,
    "string | number": Union[str, float],
}

def resolve_type(type_str: str) -> Any:
    return TYPE_MAP.get(type_str, Any)

T = TypeVar("T", bound=BaseModel)

def safe_parse(model, data: dict) -> tuple:
    from pydantic import ValidationError
    try:
        return model.model_validate(data), None
    except ValidationError as e:
        return None, e.errors()

def build_single_dictionary_model(field_name: str, spec: dict) -> type:
    """Construye un modelo Pydantic para un bloque de atributos planos."""
    fields = {}
    for attr in spec["attribute_specification"]:
        python_type = resolve_type(attr["value_type"])
        fields[attr["key"]] = (python_type, ...)  # ... = requerido
    return create_model(f"Model_{field_name}", **fields)

def build_dictionary_array_item_model(field_name: str, spec: dict) -> type:
    """Construye el modelo para cada item del array {clave, valor}."""
    array_spec = spec["array_specification"]
    key_type   = resolve_type(array_spec["type_for_item_key"])
    value_type = resolve_type(array_spec["type_for_item_value"])

    key_field_name   = array_spec["key_for_item_key"]
    value_field_name = array_spec["key_for_item_value"]

    # Lista de claves permitidas (para validación extra)
    allowed_keys = spec.get("list", None)

    fields = {
        key_field_name:   (key_type,   ...),
        value_field_name: (value_type, ...),
    }
    model = create_model(f"Item_{field_name}", **fields)

    # Validador de clave permitida si el schema define "list"
    if allowed_keys:
        def check_key(cls, v):
            if v not in allowed_keys:
                raise ValueError(f"'{v}' no está en las claves permitidas: {allowed_keys}")
            return v
        # Inyectamos el validador en el modelo dinámico
        model = type(
            f"Item_{field_name}",
            (model,),
            {f"validate_{key_field_name}": field_validator(key_field_name)(classmethod(check_key))}
        )

    return model

def build_model_from_schema(schema: dict) -> type:
    """Recorre el schema declarativo y arma el modelo Pydantic raíz."""
    root_fields = {}

    for field_name, spec in schema.items():
        # Campo simple de tipo primitivo (string, number, etc.)
        if isinstance(spec, str):
            root_fields[field_name] = (resolve_type(spec), ...)
            continue

        dict_type = spec.get("dictionary_type")

        if dict_type == "single_dictinoary":
            nested_model = build_single_dictionary_model(field_name, spec)
            root_fields[field_name] = (nested_model, ...)

        elif dict_type == "dictinoary_array":
            item_model = build_dictionary_array_item_model(field_name, spec)
            root_fields[field_name] = (List[item_model], ...)

    return create_model("DynamicRoot", **root_fields)
