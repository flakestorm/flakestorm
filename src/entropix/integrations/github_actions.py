"""
GitHub Actions Integration

Provides helpers for CI/CD integration with GitHub Actions.
"""

from __future__ import annotations

from pathlib import Path


# GitHub Action YAML template
ACTION_YAML = """name: 'Entropix Agent Test'
description: 'Run chaos testing on AI agents to verify reliability'
author: 'Entropix'

branding:
  icon: 'shield'
  color: 'purple'

inputs:
  config:
    description: 'Path to entropix.yaml configuration file'
    required: false
    default: 'entropix.yaml'
  min_score:
    description: 'Minimum robustness score to pass (0.0-1.0)'
    required: false
    default: '0.9'
  python_version:
    description: 'Python version to use'
    required: false
    default: '3.11'
  ollama_model:
    description: 'Ollama model to use for mutations'
    required: false
    default: 'qwen3:8b'

outputs:
  score:
    description: 'The robustness score achieved'
  passed:
    description: 'Whether the test passed (true/false)'
  report_path:
    description: 'Path to the generated HTML report'

runs:
  using: 'composite'
  steps:
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python_version }}
    
    - name: Install Ollama
      shell: bash
      run: |
        curl -fsSL https://ollama.ai/install.sh | sh
    
    - name: Start Ollama
      shell: bash
      run: |
        ollama serve &
        sleep 5
    
    - name: Pull Model
      shell: bash
      run: |
        ollama pull ${{ inputs.ollama_model }}
    
    - name: Install Entropix
      shell: bash
      run: |
        pip install entropix
    
    - name: Run Entropix Tests
      id: test
      shell: bash
      run: |
        SCORE=$(entropix score --config ${{ inputs.config }})
        echo "score=$SCORE" >> $GITHUB_OUTPUT
        
        if (( $(echo "$SCORE >= ${{ inputs.min_score }}" | bc -l) )); then
          echo "passed=true" >> $GITHUB_OUTPUT
        else
          echo "passed=false" >> $GITHUB_OUTPUT
          exit 1
        fi
    
    - name: Generate Report
      if: always()
      shell: bash
      run: |
        entropix run --config ${{ inputs.config }} --output html
        echo "report_path=./reports/$(ls -t ./reports/*.html | head -1)" >> $GITHUB_OUTPUT
    
    - name: Upload Report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: entropix-report
        path: ./reports/*.html
"""


# Example workflow YAML
WORKFLOW_EXAMPLE = """name: Agent Reliability Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  reliability-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Entropix
        uses: entropix/entropix-action@v1
        with:
          config: entropix.yaml
          min_score: '0.9'
"""


class GitHubActionsIntegration:
    """
    Helper class for GitHub Actions integration.
    
    Provides methods to generate action files and workflow examples.
    """
    
    @staticmethod
    def generate_action_yaml() -> str:
        """
        Generate the GitHub Action definition YAML.
        
        Returns:
            Action YAML content
        """
        return ACTION_YAML.strip()
    
    @staticmethod
    def generate_workflow_example() -> str:
        """
        Generate an example workflow that uses Entropix.
        
        Returns:
            Workflow YAML content
        """
        return WORKFLOW_EXAMPLE.strip()
    
    @staticmethod
    def save_action(output_dir: Path) -> Path:
        """
        Save the GitHub Action files to a directory.
        
        Args:
            output_dir: Directory to save action files
            
        Returns:
            Path to the action.yml file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        action_path = output_dir / "action.yml"
        action_path.write_text(ACTION_YAML.strip(), encoding="utf-8")
        
        return action_path
    
    @staticmethod
    def save_workflow_example(output_path: Path) -> Path:
        """
        Save an example workflow file.
        
        Args:
            output_path: Path to save the workflow file
            
        Returns:
            Path to the saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(WORKFLOW_EXAMPLE.strip(), encoding="utf-8")
        
        return output_path

