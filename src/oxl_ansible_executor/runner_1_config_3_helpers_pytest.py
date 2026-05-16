from oxl_ansible_executor.runner_config import ExecutionConfig


def test_append_to_list_from_none():
    """Test appending to a None value (should initialize a new list)."""
    result = ExecutionConfig.append_to_list(None, 'new_item')

    assert result == ['new_item']
    assert isinstance(result, list)


def test_append_to_list_existing_empty():
    """Test appending to an existing empty list."""
    initial_list = []
    result = ExecutionConfig.append_to_list(initial_list, 'new_item')

    assert result == ['new_item']
    assert result is initial_list  # Ensures the original object was modified in place


def test_append_to_list_existing_populated():
    """Test appending to an already populated list."""
    initial_list = ['item_1']
    result = ExecutionConfig.append_to_list(initial_list, 'item_2')

    assert result == ['item_1', 'item_2']
    assert result is initial_list


def test_append_to_list_mixed_types():
    """Test appending different object types."""
    initial_list = ['item']
    result = ExecutionConfig.append_to_list(initial_list, 42)

    assert result == ['item', 42]


# --- Tests for add_to_dict ---

def test_add_to_dict_from_none():
    """Test adding to a None value (should initialize a new dict)."""
    result = ExecutionConfig.add_to_dict(None, 'my_key', 'my_val')

    assert result == {'my_key': 'my_val'}
    assert isinstance(result, dict)


def test_add_to_dict_existing_empty():
    """Test adding to an existing empty dictionary."""
    initial_dict = {}
    result = ExecutionConfig.add_to_dict(initial_dict, 'my_key', 'my_val')

    assert result == {'my_key': 'my_val'}
    assert result is initial_dict  # Ensures the original object was modified in place


def test_add_to_dict_existing_populated():
    """Test adding a new key to an already populated dictionary."""
    initial_dict = {'key_1': 'val_1'}
    result = ExecutionConfig.add_to_dict(initial_dict, 'key_2', 'val_2')

    assert result == {'key_1': 'val_1', 'key_2': 'val_2'}
    assert result is initial_dict


def test_add_to_dict_overwrite_existing_key():
    """Test that adding a value to an existing key correctly overwrites it."""
    initial_dict = {'key_1': 'old_val'}
    result = ExecutionConfig.add_to_dict(initial_dict, 'key_1', 'new_val')

    assert result == {'key_1': 'new_val'}
    assert result is initial_dict
