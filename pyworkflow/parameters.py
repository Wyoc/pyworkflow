from dataclasses import dataclass
from typing import Any, Optional, Dict

@dataclass
class ParameterSpec:
    required: bool = False
    default: Any = None
    description: str = ""
    type: Optional[type] = None

class WorkflowParams:
    def __init__(self, **parameter_specs: Dict[str, ParameterSpec]):
        self.specs = parameter_specs

    def validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        validated_params = {}
        missing_params = []

        # Check required parameters
        for param_name, spec in self.specs.items():
            if spec.required and param_name not in params:
                missing_params.append(param_name)
            elif param_name not in params and spec.default is not None:
                validated_params[param_name] = spec.default
            elif param_name in params:
                value = params[param_name]
                if spec.type and not isinstance(value, spec.type):
                    raise TypeError(f"Parameter '{param_name}' must be of type {spec.type.__name__}, got {type(value).__name__}")
                validated_params[param_name] = value

        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

        # Add any extra parameters that weren't in specs but were provided
        for param_name, value in params.items():
            if param_name not in validated_params:
                validated_params[param_name] = value

        return validated_params