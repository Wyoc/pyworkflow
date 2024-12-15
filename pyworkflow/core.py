from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
from datetime import datetime
from pathlib import Path
import json
import pickle
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass
import signal
import sys

from .exceptions import (
    WorkflowValidationError,
    CyclicDependencyError,
    MissingDependencyError,
    WorkflowExecutionError,
    CheckpointError
)
from .utils import (
    Timer,
    Profiler,
    monitor_resources,
    with_timeout,
    ensure_directory,
    create_unique_id,
    get_dependencies_graph
)

logger = logging.getLogger(__name__)

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

        return validated_params

@dataclass
class WorkflowNode:
    func: Callable
    dependencies: Set[str]
    dependents: Set[str]
    params: Optional[WorkflowParams] = None
    timeout_seconds: Optional[int] = None
    memory_limit_mb: Optional[float] = None
    cpu_limit_percent: Optional[float] = None

class Workflow:
    _results: Dict[str, Any] = {}
    _lock = threading.Lock()
    _checkpoint_dir = Path("workflow_checkpoints")
    _status_file = _checkpoint_dir / "status.json"
    
    @classmethod
    def get_checkpoint_filename(cls, params: Dict[str, Any]) -> str:
        param_str = json.dumps(params, sort_keys=True)
        import hashlib
        params_hash = hashlib.md5(param_str.encode()).hexdigest()
        return f"checkpoint_{params_hash}.pkl"
    
    @classmethod
    def initialize(cls, params: Dict[str, Any]):
        ensure_directory(cls._checkpoint_dir)
        cls._results.clear()
        cls.load_checkpoint(params)
        
    @classmethod
    def save_checkpoint(cls, params: Dict[str, Any]):
        try:
            checkpoint_file = cls._checkpoint_dir / cls.get_checkpoint_filename(params)
            status = {
                "parameters": params,
                "last_updated": datetime.now().isoformat(),
                "completed_functions": list(cls._results.keys())
            }
            
            with cls._lock:
                with open(checkpoint_file, 'wb') as f:
                    pickle.dump(cls._results, f)
                with open(cls._status_file, 'w') as f:
                    json.dump(status, f, indent=2)
        except Exception as e:
            raise CheckpointError(f"Failed to save checkpoint: {str(e)}")
                
    @classmethod
    def load_checkpoint(cls, params: Dict[str, Any]):
        try:
            checkpoint_file = cls._checkpoint_dir / cls.get_checkpoint_filename(params)
            if checkpoint_file.exists():
                with open(checkpoint_file, 'rb') as f:
                    cls._results = pickle.load(f)
                logger.info(f"Loaded checkpoint for parameters: {params}")
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint: {str(e)}")
    
    @classmethod
    def depends_on(cls, *dependencies):
        def decorator(func):
            @wraps(func)
            @Profiler.profile
            def wrapper(params: Dict[str, Any], *args, **kwargs):
                function_name = func.__name__
                
                if function_name in cls._results:
                    logger.info(f"Using cached results for {function_name}")
                    return cls._results[function_name]
                    
                for dep in dependencies:
                    logger.info(f"Waiting for dependency {dep.__name__}")
                    while dep.__name__ not in cls._results:
                        with Timer(f"waiting_for_{dep.__name__}"):
                            time.sleep(60)
                
                logger.info(f"Starting {function_name}")
                
                with Timer(function_name):
                    try:
                        result = func(params, *args, **kwargs)
                        
                        with cls._lock:
                            cls._results[function_name] = result
                            cls.save_checkpoint(params)
                            
                        return result
                    except Exception as e:
                        raise WorkflowExecutionError(
                            f"Error in {function_name}: {str(e)}",
                            function_name=function_name,
                            original_error=e
                        )
                    
            return wrapper
        return decorator

class WorkflowGenerator:
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        
    def add_function(
        self,
        func: Callable,
        dependencies: List[Callable] = None,
        params: WorkflowParams = None,
        timeout_seconds: Optional[int] = None,
        memory_limit_mb: Optional[float] = None,
        cpu_limit_percent: Optional[float] = None
    ):
        func_name = func.__name__
        dep_names = {dep.__name__ for dep in (dependencies or [])}
        
        # Apply resource monitoring if limits are specified
        if memory_limit_mb is not None or cpu_limit_percent is not None:
            func = monitor_resources(memory_limit_mb, cpu_limit_percent)(func)
            
        # Apply timeout if specified
        if timeout_seconds is not None:
            func = with_timeout(timeout_seconds)(func)
            
        if func_name not in self.nodes:
            self.nodes[func_name] = WorkflowNode(
                func=func,
                dependencies=dep_names,
                dependents=set(),
                params=params,
                timeout_seconds=timeout_seconds,
                memory_limit_mb=memory_limit_mb,
                cpu_limit_percent=cpu_limit_percent
            )
            
        for dep_name in dep_names:
            if dep_name not in self.nodes:
                raise MissingDependencyError({func_name: [dep_name]})
            self.nodes[dep_name].dependents.add(func_name)
            
    def validate_workflow(self):
        all_deps = {dep for node in self.nodes.values() for dep in node.dependencies}
        missing_deps = all_deps - set(self.nodes.keys())
        
        if missing_deps:
            missing_dep_dict = {}
            for node_name, node in self.nodes.items():
                deps = node.dependencies & missing_deps
                if deps:
                    missing_dep_dict[node_name] = list(deps)
            raise MissingDependencyError(missing_dep_dict)
                
        # Check for cycles using get_dependencies_graph
        dep_graph = {
            name: node.dependencies
            for name, node in self.nodes.items()
        }
        
        paths = get_dependencies_graph(dep_graph)
        
        for start, path_list in paths.items():
            for path in path_list:
                if len(set(path)) != len(path):
                    raise CyclicDependencyError(path)

    def get_execution_levels(self) -> List[Set[str]]:
        levels: List[Set[str]] = []
        remaining = set(self.nodes.keys())
        
        while remaining:
            current_level = {
                node_name for node_name in remaining
                if not (self.nodes[node_name].dependencies & remaining)
            }
            
            if not current_level:
                raise WorkflowValidationError("Circular dependency detected")
                
            levels.append(current_level)
            remaining -= current_level
            
        return levels

    def generate_run_workflow(self, max_workers: int = None) -> Callable:
        self.validate_workflow()
        execution_levels = self.get_execution_levels()
        
        def run_workflow(params: Dict[str, Any]):
            workflow_id = create_unique_id()
            logger.info(f"Starting workflow {workflow_id}")
            
            # Validate parameters for each function
            validated_params = {}
            for node_name, node in self.nodes.items():
                if node.params:
                    validated_params[node_name] = node.params.validate(params)
                else:
                    validated_params[node_name] = params

            Workflow.initialize(params)
            results = {}
            
            try:
                for level in execution_levels:
                    if len(level) == 1:
                        func_name = level.pop()
                        func = self.nodes[func_name].func
                        results[func_name] = func(validated_params[func_name])
                    else:
                        with ThreadPoolExecutor(max_workers=max_workers or len(level)) as executor:
                            futures = {
                                executor.submit(
                                    self.nodes[func_name].func,
                                    validated_params[func_name]
                                ): func_name
                                for func_name in level
                            }
                            for future in futures:
                                func_name = futures[future]
                                results[func_name] = future.result()
                                
                logger.info(f"Workflow {workflow_id} completed successfully")
                Profiler.print_stats()  # Print execution statistics
                return results
                
            except KeyboardInterrupt:
                logger.warning(f"Workflow {workflow_id} interrupted by user")
                Workflow.save_checkpoint(params)  # Save progress before exit
                raise KeyboardInterrupt("Workflow was interrupted by user")
            except Exception as e:
                logger.error(f"Workflow {workflow_id} failed: {str(e)}")
                raise
                
        return run_workflow

def handle_interrupt(signum, frame):
    """Handle interrupt signal"""
    logger.warning("Received interrupt signal. Saving checkpoint before exit...")
    # Note: Can't save checkpoint here as we don't have access to current params
    sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, handle_interrupt)
signal.signal(signal.SIGTERM, handle_interrupt)