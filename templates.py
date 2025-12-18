TEMPLATES = {
    "chat": {
        "name": "💬 Chat",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ messages: [{role: string, content: string}], topic: string, quality_score: number }\n"
        ),
        "example": [
            {
                "messages": [
                    {"role": "user", "content": "Question here"},
                    {"role": "assistant", "content": "Answer here"}
                ],
                "topic": "example",
                "quality_score": 8
            }
        ]
    },

    "instruction": {
        "name": "📝 Instruction",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ instruction: string, input: string|null, output: string, complexity: string }\n"
        ),
        "example": [
            {
                "instruction": "Task description",
                "input": "Context if needed",
                "output": "Complete response",
                "complexity": "moderate"
            }
        ]
    },

    "qa": {
        "name": "❓ Q&A",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ question: string, answer: string, difficulty: string, topic: string }\n"
        ),
        "example": [
            {
                "question": "What is X?",
                "answer": "X is...",
                "difficulty": "medium",
                "topic": "subject"
            }
        ]
    },

    "dpo": {
        "name": "⚖️ DPO",
        "prompt": (
            "You are a JSON extraction engine.\n"
            "Output ONLY valid JSON. No explanations. No markdown.\n"
            "Return a JSON ARRAY. Each item must follow this schema:\n"
            "{ prompt: string, chosen: string, rejected: string, chosen_score: number, rejected_score: number }\n"
        ),
        "example": [
            {
                "prompt": "User query",
                "chosen": "High quality response",
                "rejected": "Lower quality response",
                "chosen_score": 9,
                "rejected_score": 4
            }
        ]
    }
}
