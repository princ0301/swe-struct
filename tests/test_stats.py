from swe_struct.analysis.stats import wilson_interval

def test_midpoint_interval():
    low, high = wilson_interval(5, 10)
    assert round(low, 3) == 0.237
    assert round(high, 3) == 0.763

def test_zero_successes_has_a_zero_lower_bound():
    low, high = wilson_interval(0, 10)
    assert low == 0.0
    assert round(high, 3) == 0.278

def test_no_observations_is_uninformative():
    assert wilson_interval(0, 0) == (0.0, 1.0)

def test_interval_narrows_with_more_data():
    small = wilson_interval(5, 10)
    large = wilson_interval(50, 100)
    assert large[1] - large[0] < small[1] - small[0]