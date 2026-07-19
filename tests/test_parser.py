from src.utils.tools import transcript_parse

def test_parser():
    text = "Alice: Hello\\nBob: Hi"
    result = transcript_parse(text)
    assert len(result.turns) > 0
