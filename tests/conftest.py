import pytest
from pathlib import Path
import shutil
import time
from typing import Dict, Any

from pyworkflow.core import Workflow, WorkflowGenerator
from pyworkflow.parameters import WorkflowParams, ParameterSpec


@pytest.fixture(autouse=True)
def cleanup_checkpoints():
    """Clean up checkpoint files before and after each test."""
    checkpoint_dir = Path("workflow_checkpoints")
    if checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)
    yield
    if checkpoint_dir.exists():
        shutil.rmtree(checkpoint_dir)

@pytest.fixture
def simple_workflow():
    """Create a simple workflow with two functions."""
    generator = WorkflowGenerator()
    
    @Workflow.depends_on()
    def func1(params: Dict[str, Any]):
        return f"Result 1: {params['value']}"
        
    @Workflow.depends_on(func1)
    def func2(params: Dict[str, Any]):
        return f"Result 2: {params['value']}"
        
    generator.add_function(func1)
    generator.add_function(func2, [func1])
    
    return generator

@pytest.fixture
def params_workflow():
    """Create a workflow with parameter validation."""
    generator = WorkflowGenerator()
    
    params = WorkflowParams(
        value=ParameterSpec(required=True, type=int),
        optional=ParameterSpec(default="default", type=str)
    )
    
    @Workflow.depends_on()
    def func(params: Dict[str, Any]):
        return params['value'] * 2
        
    generator.add_function(func, params=params)
    
    return generator