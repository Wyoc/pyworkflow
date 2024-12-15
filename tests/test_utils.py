def test_timer_context_manager():
    """Test the Timer context manager."""
    with Timer("test_operation") as timer:
        time.sleep(0.1)
    
    assert timer.end_time - timer.start_time >= 0.1

def test_flatten_dict():
    """Test dictionary flattening utility."""
    nested = {
        'a': 1,
        'b': {
            'c': 2,
            'd': {
                'e': 3
            }
        }
    }
    
    flat = flatten_dict(nested)
    
    assert flat == {
        'a': 1,
        'b.c': 2,
        'b.d.e': 3
    }
