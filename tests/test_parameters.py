import pytest
from pyworkflow.core import WorkflowGenerator, Workflow
from pyworkflow.exceptions import CyclicDependencyError, MissingDependencyError


def test_parameter_validation(params_workflow):
    """Test parameter validation."""
    run_workflow = params_workflow.generate_run_workflow()

    # Valid parameters
    results = run_workflow({"value": 21})
    assert results["func"] == 42

    # Test default value
    assert "optional" not in results["func"]

    # Invalid type
    with pytest.raises(TypeError):
        run_workflow({"value": "not an int"})

    # Missing required parameter
    with pytest.raises(ValueError):
        run_workflow({})


# tests/test_checkpointing.py
def test_checkpoint_creation(simple_workflow):
    """Test that checkpoints are created and loaded."""
    run_workflow = simple_workflow.generate_run_workflow()
    params = {"value": 42}

    # First run should create checkpoint
    results1 = run_workflow(params)

    # Clean results and run again
    Workflow._results.clear()

    # Second run should load from checkpoint
    results2 = run_workflow(params)

    assert results1 == results2


def test_checkpoint_recovery():
    """Test workflow recovery from checkpoint after failure."""
    generator = WorkflowGenerator()
    results = []

    @Workflow.depends_on()
    def success(params):
        results.append("success")
        return True

    @Workflow.depends_on(success)
    def fail(params):
        results.append("fail")
        raise ValueError("Deliberate failure")

    generator.add_function(success)
    generator.add_function(fail, [success])

    run_workflow = generator.generate_run_workflow()

    # First run should fail
    with pytest.raises(ValueError):
        run_workflow({})

    # Clear results list but keep checkpoint
    results.clear()

    # Second run should skip successful function
    with pytest.raises(ValueError):
        run_workflow({})

    # The successful function should not have run again
    assert results == ["fail"]
