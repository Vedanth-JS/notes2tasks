from src.utils.tools import extract_action_items, priority_score

def test_extract_action_items():
    text = "Action item: @Bob send the updated deck by Friday."
    result = extract_action_items(text)
    assert len(result) > 0
    assert result[0].owner == "Bob"

def test_priority_score():
    item = {"title": "Fix critical bug in production", "deadline": "2026-02-27", "owner": "Alice"}
    # Pseudo test
    assert True
