TEMPLATES = {
    "chat": {
        "name": "💬 Chat",
        "prompt": """Extract conversational exchanges from the text.
Return JSON array with: messages (array of role/content), topic, quality_score.
ONLY return valid JSON array, no markdown.""",
        "example": {
            "messages": [
                {"role": "user", "content": "Question here"},
                {"role": "assistant", "content": "Answer here"}
            ],
            "topic": "example",
            "quality_score": 8
        }
    },
    
    "instruction": {
        "name": "📝 Instruction",
        "prompt": """Extract instruction-response pairs.
Return JSON array with: instruction, input (optional), output, complexity.
ONLY return valid JSON array.""",
        "example": {
            "instruction": "Task description",
            "input": "Context if needed",
            "output": "Complete response",
            "complexity": "moderate"
        }
    },
    
    "qa": {
        "name": "❓ Q&A",
        "prompt": """Extract question-answer pairs.
Return JSON array with: question, answer, difficulty, topic.
ONLY return valid JSON array.""",
        "example": {
            "question": "What is X?",
            "answer": "X is...",
            "difficulty": "medium",
            "topic": "subject"
        }
    },
    
    "dpo": {
        "name": "⚖️ DPO",
        "prompt": """Create preference pairs with chosen/rejected responses.
Return JSON array with: prompt, chosen, rejected, chosen_score, rejected_score.
ONLY return valid JSON array.""",
        "example": {
            "prompt": "User query",
            "chosen": "High quality response",
            "rejected": "Lower quality response",
            "chosen_score": 9,
            "rejected_score": 4
        }
    }
}