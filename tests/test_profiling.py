def test_execution_profiling():
    """Test execution time profiling."""
    generator = WorkflowGenerator()
    
    @Workflow.depends_on()
    def timed_function(params):
        time.sleep(0.1)
        return True
        
    generator.add_function(timed_function)
    
    run_workflow = generator.generate_run_workflow()
    run_workflow({})
    
    stats = Profiler.get_stats()
    assert 'timed_function' in stats
    assert stats['timed_function']['total'] >= 0.1
