from pyworkflow.core import Workflow, WorkflowGenerator
from pyworkflow.exceptions import CyclicDependencyError, MissingDependencyError
import pytest
import time


def test_simple_workflow_execution(simple_workflow):
    """Test basic workflow execution."""
    run_workflow = simple_workflow.generate_run_workflow()
    results = run_workflow({"value": 42})

    assert len(results) == 2
    assert results["func1"] == "Result 1: 42"
    assert results["func2"] == "Result 2: 42"


def test_workflow_dependencies(simple_workflow):
    """Test that dependencies are executed in correct order."""
    execution_order = []

    @Workflow.depends_on()
    def first(params):
        execution_order.append("first")
        return 1

    @Workflow.depends_on(first)
    def second(params):
        execution_order.append("second")
        return 2

    generator = WorkflowGenerator()
    generator.add_function(first)
    generator.add_function(second, [first])

    run_workflow = generator.generate_run_workflow()
    run_workflow({})

    assert execution_order == ["first", "second"]


def test_parallel_execution():
    """Test parallel execution of independent functions."""
    generator = WorkflowGenerator()
    results = []

    @Workflow.depends_on()
    def slow1(params):
        time.sleep(1)
        results.append("slow1")
        return 1

    @Workflow.depends_on()
    def slow2(params):
        time.sleep(1)
        results.append("slow2")
        return 2

    generator.add_function(slow1)
    generator.add_function(slow2)

    start_time = time.time()
    run_workflow = generator.generate_run_workflow(max_workers=2)
    run_workflow({})
    duration = time.time() - start_time

    # Both functions should run in parallel, taking ~1 second total
    assert duration < 1.5  # Allow some overhead
    assert set(results) == {"slow1", "slow2"}
