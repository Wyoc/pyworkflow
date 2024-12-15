from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
from datetime import datetime
import time
import signal
import sys
from pathlib import Path
import json
import pickle
from typing import Dict, Any, Optional, List, Callable, Set, Tuple, Union
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class WorkflowNode:
    func: Callable
    dependencies: Set[str]
    dependents: Set[str]


class WorkflowGenerator:
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}

    def add_function(self, func: Callable, dependencies: List[Callable] = None):
        """Add a function to the workflow with its dependencies"""
        func_name = func.__name__
        dep_names = {dep.__name__ for dep in (dependencies or [])}

        if func_name not in self.nodes:
            self.nodes[func_name] = WorkflowNode(func, dep_names, set())

        for dep_name in dep_names:
            if dep_name not in self.nodes:
                raise ValueError(f"Dependency {dep_name} not found in workflow")
            self.nodes[dep_name].dependents.add(func_name)

    def validate_workflow(self):
        """Check for cycles and missing dependencies"""
        all_deps = {dep for node in self.nodes.values() for dep in node.dependencies}
        missing_deps = all_deps - set(self.nodes.keys())
        if missing_deps:
            raise ValueError(f"Missing dependencies: {missing_deps}")

        def has_cycle(node_name: str, visited: Set[str], path: Set[str]) -> bool:
            if node_name in path:
                return True
            if node_name in visited:
                return False

            visited.add(node_name)
            path.add(node_name)

            node = self.nodes[node_name]
            for dep in node.dependencies:
                if has_cycle(dep, visited, path):
                    return True

            path.remove(node_name)
            return False

        visited = set()
        for node_name in self.nodes:
            if has_cycle(node_name, visited, set()):
                raise ValueError("Cycle detected in workflow")

    def get_execution_levels(self) -> List[Set[str]]:
        """Group functions by their execution level"""
        levels: List[Set[str]] = []
        remaining = set(self.nodes.keys())

        while remaining:
            current_level = {
                node_name
                for node_name in remaining
                if not (self.nodes[node_name].dependencies & remaining)
            }

            if not current_level:
                raise ValueError("Circular dependency detected")

            levels.append(current_level)
            remaining -= current_level

        return levels

    def generate_workflow_class(self):
        """Generate the Workflow class"""

        class Workflow:
            _results: Dict[str, Any] = {}
            _lock = threading.Lock()
            _checkpoint_dir = Path("workflow_checkpoints")
            _status_file = _checkpoint_dir / "status.json"

            @classmethod
            def get_checkpoint_filename(cls, params: Dict[str, Any]) -> str:
                """Generate a unique filename based on parameters"""
                # Sort parameters to ensure consistent filename
                param_str = json.dumps(params, sort_keys=True)
                import hashlib

                # Create a hash of parameters for filename
                params_hash = hashlib.md5(param_str.encode()).hexdigest()
                return f"checkpoint_{params_hash}.pkl"

            @classmethod
            def initialize(cls, params: Dict[str, Any]):
                cls._checkpoint_dir.mkdir(exist_ok=True)
                cls._results.clear()
                cls.load_checkpoint(params)

            @classmethod
            def save_checkpoint(cls, params: Dict[str, Any]):
                checkpoint_file = cls._checkpoint_dir / cls.get_checkpoint_filename(
                    params
                )
                status = {
                    "parameters": params,
                    "last_updated": datetime.now().isoformat(),
                    "completed_functions": list(cls._results.keys()),
                }

                with cls._lock:
                    with open(checkpoint_file, "wb") as f:
                        pickle.dump(cls._results, f)
                    with open(cls._status_file, "w") as f:
                        json.dump(status, f, indent=2)

            @classmethod
            def load_checkpoint(cls, params: Dict[str, Any]):
                checkpoint_file = cls._checkpoint_dir / cls.get_checkpoint_filename(
                    params
                )
                if checkpoint_file.exists():
                    with open(checkpoint_file, "rb") as f:
                        cls._results = pickle.load(f)
                    logger.info(f"Loaded checkpoint for parameters: {params}")

            @classmethod
            def depends_on(cls, *dependencies):
                def decorator(func):
                    @wraps(func)
                    def wrapper(params: Dict[str, Any], *args, **kwargs):
                        function_name = func.__name__

                        if function_name in cls._results:
                            logger.info(f"Using cached results for {function_name}")
                            return cls._results[function_name]

                        for dep in dependencies:
                            logger.info(f"Waiting for dependency {dep.__name__}")
                            while dep.__name__ not in cls._results:
                                time.sleep(60)

                        logger.info(f"Starting {function_name}")
                        start_time = time.time()

                        try:
                            result = func(params, *args, **kwargs)
                            execution_time = time.time() - start_time
                            logger.info(
                                f"{function_name} completed in {execution_time/3600:.2f} hours"
                            )

                            with cls._lock:
                                cls._results[function_name] = result
                                cls.save_checkpoint(params)

                            return result
                        except Exception as e:
                            logger.error(
                                f"Error in {function_name}: {str(e)}", exc_info=True
                            )
                            raise

                    return wrapper

                return decorator

        return Workflow

    def generate_run_workflow(self, max_workers: int = None) -> Callable:
        """Generate the run_workflow function"""
        self.validate_workflow()
        execution_levels = self.get_execution_levels()
        Workflow = self.generate_workflow_class()

        def run_workflow(params: Dict[str, Any]):
            logger.info(f"Starting workflow with parameters: {params}")
            Workflow.initialize(params)
            results = {}

            try:
                for level in execution_levels:
                    if len(level) == 1:
                        func_name = level.pop()
                        func = self.nodes[func_name].func
                        results[func_name] = func(params)
                    else:
                        with ThreadPoolExecutor(
                            max_workers=max_workers or len(level)
                        ) as executor:
                            futures = {
                                executor.submit(
                                    self.nodes[func_name].func, params
                                ): func_name
                                for func_name in level
                            }
                            for future in futures:
                                func_name = futures[future]
                                results[func_name] = future.result()

                logger.info("Workflow completed successfully")
                return results

            except KeyboardInterrupt:
                logger.warning("Workflow interrupted by user")
                raise KeyboardInterrupt("Workflow was interrupted by user")
            except Exception as e:
                logger.error(f"Workflow failed: {str(e)}", exc_info=True)
                raise

        return run_workflow


# Example usage
def example_usage():
    generator = WorkflowGenerator()

    @generator.generate_workflow_class().depends_on()
    def process_data(params: Dict[str, Any]):
        date = params.get("date")
        region = params.get("region", "default")
        logger.info(f"Processing data for date {date} in region {region}")
        time.sleep(10)
        return f"Processed data for {date} in {region}"

    @generator.generate_workflow_class().depends_on(process_data)
    def analyze_results(params: Dict[str, Any]):
        model_type = params.get("model_type", "default")
        logger.info(f"Analyzing with model {model_type}")
        time.sleep(15)
        return f"Analysis done with {model_type}"

    @generator.generate_workflow_class().depends_on(process_data)
    def generate_reports(params: Dict[str, Any]):
        report_format = params.get("report_format", "pdf")
        logger.info(f"Generating {report_format} reports")
        time.sleep(12)
        return f"Reports generated in {report_format}"

    # Add functions to workflow
    generator.add_function(process_data)
    generator.add_function(analyze_results, [process_data])
    generator.add_function(generate_reports, [process_data])

    # Generate run_workflow function
    run_workflow = generator.generate_run_workflow(max_workers=2)

    # Example parameters
    params = {
        "date": "2024-12-15",
        "region": "Europe",
        "model_type": "advanced",
        "report_format": "excel",
    }

    try:
        results = run_workflow(params)
        logger.info("Final Results:")
        for func_name, result in results.items():
            logger.info(f"{func_name}: {result}")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    example_usage()
