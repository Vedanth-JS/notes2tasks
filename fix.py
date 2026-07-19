import os

mapping = {
    'from src.db': 'from src.database.db',
    'from src.schemas': 'from src.models.schemas',
    'from src.agents import': 'from src.agents.agents import',
    'from src.baseline_single_agent': 'from src.agents.baseline_single_agent',
    'from src.logging_utils': 'from src.utils.logging_utils',
    'from src.guardrails': 'from src.utils.guardrails',
    'from src.tools': 'from src.utils.tools',
    'from src.evaluation import': 'from src.evaluation.evaluation import',
    'from src.analysis': 'from src.evaluation.analysis',
    'from src.scenarios': 'from src.evaluation.scenarios',
    'from .db': 'from src.database.db',
    'from .schemas': 'from src.models.schemas',
    'from .agents': 'from src.agents.agents',
    'from .baseline_single_agent': 'from src.agents.baseline_single_agent',
    'from .logging_utils': 'from src.utils.logging_utils',
    'from .guardrails': 'from src.utils.guardrails',
    'from .tools': 'from src.utils.tools',
    'from .evaluation': 'from src.evaluation.evaluation',
    'from .analysis': 'from src.evaluation.analysis',
    'from .scenarios': 'from src.evaluation.scenarios',
    'from .orchestrator': 'from src.orchestrator',
    'from .state_machine': 'from src.state_machine',
}

def fix():
    for root, dirs, files in os.walk('.'):
        if '.venv' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.py') and file != 'fix.py':
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    continue
                
                new_content = content
                for old, new in mapping.items():
                    new_content = new_content.replace(old, new)
                    
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed {path}")

fix()
