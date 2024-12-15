from typing import Any, List, Dict, Optional

class WorkflowException(Exception):
    """Base exception class for all workflow-related exceptions."""
    pass

class WorkflowValidationError(WorkflowException):
    """Raised when workflow validation fails (cycles, missing dependencies, etc.)."""
    pass

class ParameterValidationError(WorkflowException):
    """Raised when parameter validation fails."""
    def __init__(self, message: str, parameter_name: Optional[str] = None, 
                 function_name: Optional[str] = None, expected_type: Optional[type] = None,
                 received_value: Any = None):
        self.parameter_name = parameter_name
        self.function_name = function_name
        self.expected_type = expected_type
        self.received_value = received_value
        super().__init__(message)

class CyclicDependencyError(WorkflowValidationError):
    """Raised when a circular dependency is detected in the workflow."""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")

class MissingDependencyError(WorkflowValidationError):
    """Raised when a dependency is missing from the workflow."""
    def __init__(self, missing_deps: Dict[str, List[str]]):
        self.missing_deps = missing_deps
        deps_str = "\n".join(
            f"- {func} requires: {', '.join(deps)}"
            for func, deps in missing_deps.items()
        )
        super().__init__(f"Missing dependencies:\n{deps_str}")

class WorkflowExecutionError(WorkflowException):
    """Raised when there's an error during workflow execution."""
    def __init__(self, message: str, function_name: Optional[str] = None, 
                 original_error: Optional[Exception] = None):
        self.function_name = function_name
        self.original_error = original_error
        super().__init__(message)

class CheckpointError(WorkflowException):
    """Raised when there's an error with checkpointing operations."""
    pass

class FunctionTimeoutError(WorkflowExecutionError):
    """Raised when a function execution exceeds its timeout."""
    def __init__(self, function_name: str, timeout: int):
        super().__init__(
            f"Function '{function_name}' exceeded timeout of {timeout} seconds",
            function_name=function_name
        )

class ResourceExhaustedError(WorkflowExecutionError):
    """Raised when a function exhausts its allocated resources (memory, CPU, etc.)."""
    def __init__(self, function_name: str, resource_type: str, limit: Any, 
                 current_usage: Any):
        self.resource_type = resource_type
        self.limit = limit
        self.current_usage = current_usage
        super().__init__(
            f"Function '{function_name}' exceeded {resource_type} limit. "
            f"Limit: {limit}, Current usage: {current_usage}",
            function_name=function_name
        )

class DependencyExecutionError(WorkflowExecutionError):
    """Raised when a dependency fails and prevents execution of dependent functions."""
    def __init__(self, function_name: str, failed_dependency: str, 
                 original_error: Optional[Exception] = None):
        self.failed_dependency = failed_dependency
        super().__init__(
            f"Cannot execute '{function_name}' due to failure in dependency '{failed_dependency}'",
            function_name=function_name,
            original_error=original_error
        )

class ParallelExecutionError(WorkflowExecutionError):
    """Raised when there's an error in parallel execution of functions."""
    def __init__(self, failed_functions: Dict[str, Exception]):
        self.failed_functions = failed_functions
        failures_str = "\n".join(
            f"- {func}: {str(error)}"
            for func, error in failed_functions.items()
        )
        super().__init__(f"Multiple functions failed during parallel execution:\n{failures_str}")
