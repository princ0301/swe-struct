from swe_struct.core.ids import config_hash, run_id

def test_config_hash_ignores_key_order():
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})

def test_config_hash_changes_with_value():
    assert config_hash({"a": 1}) != config_hash({"a": 2})

def test_run_id_is_deterministic_and_seed_sensitive():
    first = run_id("e4b", "A2", "task-1", 0, "abc")
    assert first == run_id("e4b", "A2", "task-1", 0, "abc")
    assert first != run_id("e4b", "A2", "task-1", 1, "abc")