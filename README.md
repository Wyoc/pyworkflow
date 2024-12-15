# Workflow Generator

A flexible Python library for creating and managing workflows with parameter validation, resource monitoring, and checkpointing capabilities.

## Features

- **Dependency Management**: Define complex workflows with dependencies between tasks
- **Parameter Validation**: Validate input parameters for each function in the workflow
- **Resource Monitoring**: Track memory and CPU usage of workflow tasks
- **Checkpointing**: Automatically save and resume workflow progress
- **Parallel Execution**: Run independent tasks concurrently
- **Performance Profiling**: Monitor execution times and resource usage
- **Error Handling**: Comprehensive error handling and reporting
- **Type Safety**: Full type hints support

## Installation

Using Poetry:

```bash
poetry add workflow-generator
```

Or using pip:

```bash
pip install workflow-generator
```

## Quick Start

Here's a simple example of how to use the workflow generator:

```python
from workflow_generator import WorkflowGenerator, Workflow, WorkflowParams, ParameterSpec

# Define parameter specifications
data_params = WorkflowParams(
    date=ParameterSpec(required=True, type=str),
    region=ParameterSpec(required=True, type=str),
    batch_size=ParameterSpec(default=1000, type=int)
)

# Define workflow functions
@Workflow.depends_on()
def process_data(params):
    date = params['date']
    region = params['region']
    batch_size = params['batch_size']
    # Process data
    return f"Processed data for {date} in {region}"

@Workflow.depends_on(process_data)
def analyze_results(params):
    # Analyze the processed data
    return "Analysis complete"

# Create workflow
generator = WorkflowGenerator()
generator.add_function(process_data, params=data_params)
generator.add_function(analyze_results, [process_data])

# Generate and run workflow
run_workflow = generator.generate_run_workflow(max_workers=2)

# Execute workflow
results = run_workflow({
    'date': '2024-12-15',
    'region': 'Europe',
    'batch_size': 500
})
```

## Advanced Usage

### Resource Monitoring

Monitor memory and CPU usage of your functions:

```python
generator.add_function(
    process_data,
    memory_limit_mb=1000,
    cpu_limit_percent=90,
    timeout_seconds=3600
)
```

### Checkpointing

Workflows automatically save their progress and can be resumed:

```python
try:
    results = run_workflow(params)
except KeyboardInterrupt:
    # Progress is automatically saved
    # Resume later with the same parameters
    results = run_workflow(params)  # Will continue from last checkpoint
```

### Parameter Validation

Define complex parameter requirements:

```python
params = WorkflowParams(
    date=ParameterSpec(
        required=True,
        type=str,
        description="Processing date in YYYY-MM-DD format"
    ),
    region=ParameterSpec(
        required=True,
        type=str,
        description="Geographic region to process"
    ),
    options=ParameterSpec(
        default={'detailed': True},
        type=dict,
        description="Additional processing options"
    )
)
```

## Project Structure

```
workflow-generator/
├── workflow_generator/
│   ├── __init__.py
│   ├── core.py         # Main workflow implementation
│   ├── parameters.py   # Parameter validation
│   ├── utils.py        # Utility functions
│   └── exceptions.py   # Custom exceptions
├── tests/
│   └── ...
├── examples/
│   └── ...
└── docs/
    └── ...
```

## Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/workflow-generator.git
cd workflow-generator
```

2. Install dependencies:
```bash
poetry install
```

3. Run tests:
```bash
poetry run pytest
```

4. Format code:
```bash
poetry run black .
poetry run isort .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Error Handling

The library provides custom exceptions for different error cases:

```python
from workflow_generator.exceptions import (
    WorkflowValidationError,
    ParameterValidationError,
    ResourceExhaustedError
)

try:
    results = run_workflow(params)
except ParameterValidationError as e:
    print(f"Parameter validation failed: {e}")
except ResourceExhaustedError as e:
    print(f"Resource limit exceeded: {e}")
except WorkflowValidationError as e:
    print(f"Workflow validation failed: {e}")
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Requirements

- Python 3.8 or higher
- Dependencies listed in pyproject.toml

## Support

For support, please:
1. Check the documentation
2. Search existing issues
3. Create a new issue if needed

## Acknowledgments

Thanks to all contributors who have helped with the development of this library.