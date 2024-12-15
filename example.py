from pyworkflow.core import *
from pyworkflow.parameters import *
import time
import logging

logger = logging.getLogger(__name__)


def example_usage():
    logger.info("Define parameter specifications")
    data_processing_params = WorkflowParams(
        date=ParameterSpec(required=True, type=str, description="Processing date in YYYY-MM-DD format"),
        region=ParameterSpec(required=True, type=str, description="Geographic region to process"),
        batch_size=ParameterSpec(default=1000, type=int, description="Number of records to process at once")
    )

    analysis_params = WorkflowParams(
        model_type=ParameterSpec(required=True, type=str, description="Type of analysis model to use"),
        threshold=ParameterSpec(default=0.5, type=float, description="Analysis threshold")
    )

    reporting_params = WorkflowParams(
        report_format=ParameterSpec(default="pdf", type=str, description="Output format for reports"),
        include_graphs=ParameterSpec(default=True, type=bool, description="Whether to include graphs in reports")
    )

    @Workflow.depends_on()
    def process_data(params: Dict[str, Any]):
        logger.info(f"Processing data for date {params['date']} in region {params['region']}")
        logger.info(f"Using batch size: {params['batch_size']}")
        time.sleep(10)
        return f"Processed data for {params['date']} in {params['region']}"
        
    @Workflow.depends_on(process_data)
    def analyze_results(params: Dict[str, Any]):
        logger.info(f"Analyzing with model {params['model_type']}, threshold {params['threshold']}")
        time.sleep(15)
        return f"Analysis done with {params['model_type']}"
        
    @Workflow.depends_on(process_data)
    def generate_reports(params: Dict[str, Any]):
        logger.info(f"Generating {params['report_format']} reports")
        logger.info(f"Including graphs: {params['include_graphs']}")
        time.sleep(12)
        return f"Reports generated in {params['report_format']}"
        
    # Create workflow
    generator = WorkflowGenerator()
    
    # Add functions with their parameter specifications
    generator.add_function(process_data, params=data_processing_params)
    generator.add_function(analyze_results, [process_data], params=analysis_params)
    generator.add_function(generate_reports, [process_data], params=reporting_params)
    
    # Generate run_workflow function
    run_workflow = generator.generate_run_workflow(max_workers=2)
    
    # Example parameters
    params = {
        'date': '2024-12-15',
        'region': 'Europe',
        'model_type': 'advanced',
        'report_format': 'excel',
        'batch_size': 500,
        'threshold': 0.7,
        'include_graphs': True
    }
    
    try:
        results = run_workflow(params)
        logger.info("Final Results:")
        for func_name, result in results.items():
            logger.info(f"{func_name}: {result}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    logger.info("Starting workflow...")
    example_usage()