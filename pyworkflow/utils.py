"""example/
```python
@monitor_resources(memory_limit_mb=1000, cpu_limit_percent=90)
@with_timeout(60)
@Profiler.profile
def example_function(x: int) -> int:
    with Timer("example_function"):
        time.sleep(1)
        return x * 2

try:
    result = example_function(5)
    print(f"Result: {result}")
    Profiler.print_stats()
except (ResourceExhaustedError, FunctionTimeoutError) as e:
    print(f"Error: {e}")
```
"""
import os
import time
import psutil
import logging
from typing import Any, Dict, Callable, Optional, List, Set, TypeVar
from pathlib import Path
from datetime import datetime, timedelta
import json
from functools import wraps
import threading
from concurrent.futures import ThreadPoolExecutor

from .exceptions import ResourceExhaustedError, FunctionTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for function returns

def get_memory_usage(pid: Optional[int] = None) -> float:
    """Get memory usage for a process in MB."""
    process = psutil.Process(pid or os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def get_cpu_usage(pid: Optional[int] = None) -> float:
    """Get CPU usage percentage for a process."""
    process = psutil.Process(pid or os.getpid())
    return process.cpu_percent(interval=1.0)

def monitor_resources(
    memory_limit_mb: float = float('inf'),
    cpu_limit_percent: float = float('inf')
) -> Callable:
    """Decorator to monitor resource usage of a function."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            pid = os.getpid()
            
            def check_resources():
                while True:
                    memory_usage = get_memory_usage(pid)
                    cpu_usage = get_cpu_usage(pid)
                    
                    if memory_usage > memory_limit_mb:
                        raise ResourceExhaustedError(
                            func.__name__, 'memory',
                            f"{memory_limit_mb}MB",
                            f"{memory_usage:.1f}MB"
                        )
                    
                    if cpu_usage > cpu_limit_percent:
                        raise ResourceExhaustedError(
                            func.__name__, 'CPU',
                            f"{cpu_limit_percent}%",
                            f"{cpu_usage:.1f}%"
                        )
                    
                    time.sleep(1)
            
            monitor_thread = threading.Thread(target=check_resources, daemon=True)
            monitor_thread.start()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def with_timeout(timeout_seconds: int) -> Callable:
    """Decorator to add timeout to a function."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except TimeoutError:
                    raise FunctionTimeoutError(func.__name__, timeout_seconds)
        return wrapper
    return decorator

class Timer:
    """Context manager for timing code blocks."""
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"{self.name} took {duration:.2f} seconds")

def create_unique_id() -> str:
    """Create a unique identifier for workflow runs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"workflow_{timestamp}_{os.getpid()}"

def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists and return the Path object."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def format_time_delta(delta: timedelta) -> str:
    """Format a timedelta into a human-readable string."""
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    items: List[tuple] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def get_dependencies_graph(dependencies: Dict[str, Set[str]]) -> Dict[str, List[List[str]]]:
    """Get all possible paths through a dependency graph."""
    def find_paths(start: str, end: str, path: List[str]) -> List[List[str]]:
        path = path + [start]
        if start == end:
            return [path]
        paths = []
        for node in dependencies.get(start, []):
            if node not in path:
                new_paths = find_paths(node, end, path)
                paths.extend(new_paths)
        return paths

    result = {}
    nodes = set().union(*[{k} | v for k, v in dependencies.items()])
    
    for start in nodes:
        result[start] = []
        for end in nodes:
            if start != end:
                paths = find_paths(start, end, [])
                if paths:
                    result[start].extend(paths)
    
    return result

class Profiler:
    """Simple profiler for tracking function execution times."""
    _timings: Dict[str, List[float]] = {}
    
    @classmethod
    def profile(cls, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if func.__name__ not in cls._timings:
                cls._timings[func.__name__] = []
            cls._timings[func.__name__].append(duration)
            
            return result
        return wrapper
    
    @classmethod
    def get_stats(cls) -> Dict[str, Dict[str, float]]:
        stats = {}
        for func_name, times in cls._timings.items():
            if times:
                stats[func_name] = {
                    'count': len(times),
                    'total': sum(times),
                    'average': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times)
                }
        return stats
    
    @classmethod
    def print_stats(cls):
        stats = cls.get_stats()
        for func_name, func_stats in stats.items():
            print(f"\nFunction: {func_name}")
            print(f"  Count: {func_stats['count']}")
            print(f"  Total time: {func_stats['total']:.2f}s")
            print(f"  Average time: {func_stats['average']:.2f}s")
            print(f"  Min time: {func_stats['min']:.2f}s")
            print(f"  Max time: {func_stats['max']:.2f}s")

