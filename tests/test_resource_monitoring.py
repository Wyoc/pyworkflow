def test_memory_limit():
    """Test memory limit enforcement."""
    generator = WorkflowGenerator()
    
    @Workflow.depends_on()
    def memory_intensive(params):
        # Create a large list to consume memory
        large_list = [0] * (10**7)
        return len(large_list)
        
    generator.add_function(
        memory_intensive,
        memory_limit_mb=1  # Very low limit
    )
    
    run_workflow = generator.generate_run_workflow()
    
    with pytest.raises(ResourceExhaustedError):
        run_workflow({})

def test_timeout():
    """Test function timeout."""
    generator = WorkflowGenerator()
    
    @Workflow.depends_on()
    def slow_function(params):
        time.sleep(2)
        return True
        
    generator.add_function(
        slow_function,
        timeout_seconds=1  # Timeout after 1 second
    )
    
    run_workflow = generator.generate_run_workflow()
    
    with pytest.raises(FunctionTimeoutError):
        run_workflow({})
