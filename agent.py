from crewai import Agent, Task, Crew, Process
from langchain_anthropic import ChatAnthropic
import json

def validate_dataset(dataset, api_key):
    """Run CrewAI validation"""
    
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=api_key,
        temperature=0.3
    )
    
    # Single validator agent
    validator = Agent(
        role="Dataset Validator",
        goal="Check quality, consistency, bias, and format",
        backstory="Expert in dataset validation for ML training",
        llm=llm,
        verbose=False
    )
    
    # Validation task
    sample = dataset[:5]  # Check first 5 entries
    task = Task(
        description=f"""Validate this dataset:
{json.dumps(sample, indent=2)}

Check: quality, duplicates, bias, format compliance.
Provide: score (1-10), issues found, recommendations.""",
        agent=validator,
        expected_output="Validation report with score and issues"
    )
    
    crew = Crew(agents=[validator], tasks=[task], process=Process.sequential)
    return crew.kickoff()