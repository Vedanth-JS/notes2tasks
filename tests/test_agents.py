from src.agents.agents import TaskClassifierAgent, PriorityAgent
from src.models.schemas import ActionItem

def test_classifier_agent():
    agent = TaskClassifierAgent()
    assert agent is not None

def test_priority_agent():
    agent = PriorityAgent()
    assert agent is not None
