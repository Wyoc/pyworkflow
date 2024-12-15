import pytest
from pyworkflow.core import WorkflowGenerator, Workflow
from pyworkflow.exceptions import CyclicDependencyError, MissingDependencyError


def test_cyclic_dependency_detection():
    """Test detection of circular dependencies."""
    generator = WorkflowGenerator()

    @Workflow.depends_on()
    def func1(params):
        return 1

    @Workflow.depends_on(func1)
    def func2(params):
        return 2

    generator.add_function(func1)
    generator.add_function(func2, [func1])

    # Try to create a cycle
    with pytest.raises(CyclicDependencyError):
        generator.add_function(func1, [func2])  # This creates a cycle


def test_missing_dependency_detection():
    """Test detection of missing dependencies."""
    generator = WorkflowGenerator()

    @Workflow.depends_on()
    def existing(params):
        return True

    @Workflow.depends_on()
    def dependent(params):
        return True

    # Add function with non-existent dependency
    with pytest.raises(MissingDependencyError):
        generator.add_function(dependent, [existing, "non_existent_function"])
