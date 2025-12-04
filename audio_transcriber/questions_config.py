"""
Predefined questions for call quality evaluation.
Each question has:
- id: Unique identifier
- category: Question category for grouping
- question: The question text
- description: Additional context for the LLM
- weight: Importance weight (1-5)
"""

PREDEFINED_QUESTIONS = [
    # Greeting & Introduction
    {
        "id": "greeting",
        "category": "Opening",
        "question": "Did the agent greet the customer properly?",
        "description": "Check if the agent used a professional greeting, introduced themselves, and/or mentioned the company name.",
        "weight": 3
    },
    {
        "id": "customer_name",
        "category": "Opening",
        "question": "Did the agent ask for or use the customer's name?",
        "description": "Check if the agent personalized the conversation by asking for or using the customer's name.",
        "weight": 2
    },
    
    # Issue Handling
    {
        "id": "issue_understood",
        "category": "Issue Handling",
        "question": "Did the agent understand the customer's issue/query?",
        "description": "Check if the agent correctly identified and acknowledged the customer's problem or request.",
        "weight": 5
    },
    {
        "id": "issue_resolved",
        "category": "Issue Handling",
        "question": "Was the customer's issue resolved?",
        "description": "Determine if the issue was fully resolved, partially resolved, or left unresolved.",
        "weight": 5
    },
    {
        "id": "correct_info",
        "category": "Issue Handling",
        "question": "Did the agent provide accurate and relevant information?",
        "description": "Check if the information provided by the agent was correct and helpful for the customer's query.",
        "weight": 4
    },
    
    # Communication
    {
        "id": "clear_communication",
        "category": "Communication",
        "question": "Was the agent's communication clear and professional?",
        "description": "Evaluate if the agent communicated clearly without jargon, was polite, and maintained professionalism.",
        "weight": 4
    },
    {
        "id": "active_listening",
        "category": "Communication",
        "question": "Did the agent demonstrate active listening?",
        "description": "Check if the agent acknowledged customer concerns, didn't interrupt, and responded appropriately.",
        "weight": 3
    },
    {
        "id": "empathy",
        "category": "Communication",
        "question": "Did the agent show empathy towards the customer?",
        "description": "Look for empathetic statements, understanding of customer frustration, or supportive language.",
        "weight": 3
    },
    
    # Process & Compliance
    {
        "id": "verification",
        "category": "Compliance",
        "question": "Did the agent verify customer identity (if required)?",
        "description": "Check if the agent asked for verification details like account number, phone, or other identifiers.",
        "weight": 4
    },
    {
        "id": "hold_procedure",
        "category": "Compliance",
        "question": "Did the agent follow proper hold/transfer procedures?",
        "description": "If the call had holds or transfers, check if the agent asked permission and explained the reason.",
        "weight": 2
    },
    
    # Closing
    {
        "id": "next_steps",
        "category": "Closing",
        "question": "Did the agent explain next steps or follow-up actions?",
        "description": "Check if the agent clearly explained what will happen next or what the customer needs to do.",
        "weight": 4
    },
    {
        "id": "additional_help",
        "category": "Closing",
        "question": "Did the agent ask if there's anything else to help with?",
        "description": "Check if the agent offered additional assistance before ending the call.",
        "weight": 3
    },
    {
        "id": "proper_closing",
        "category": "Closing",
        "question": "Did the agent close the call professionally?",
        "description": "Check for proper closing statement, thank you, and professional goodbye.",
        "weight": 3
    },
    
    # Customer Sentiment
    {
        "id": "customer_satisfied",
        "category": "Outcome",
        "question": "Did the customer seem satisfied at the end of the call?",
        "description": "Based on the customer's tone and responses, determine if they seemed satisfied with the interaction.",
        "weight": 5
    },
    {
        "id": "customer_frustrated",
        "category": "Outcome",
        "question": "Did the customer express frustration or dissatisfaction?",
        "description": "Look for signs of customer frustration, complaints, or negative sentiment during the call.",
        "weight": 4
    },
]

# Question categories with descriptions
QUESTION_CATEGORIES = {
    "Opening": {
        "description": "How the call was initiated",
        "icon": "fa-door-open",
        "color": "#6366f1"
    },
    "Issue Handling": {
        "description": "How the customer's issue was addressed",
        "icon": "fa-wrench",
        "color": "#f59e0b"
    },
    "Communication": {
        "description": "Quality of communication",
        "icon": "fa-comments",
        "color": "#10b981"
    },
    "Compliance": {
        "description": "Adherence to procedures",
        "icon": "fa-clipboard-check",
        "color": "#8b5cf6"
    },
    "Closing": {
        "description": "How the call was concluded",
        "icon": "fa-flag-checkered",
        "color": "#ec4899"
    },
    "Outcome": {
        "description": "Overall call outcome",
        "icon": "fa-chart-line",
        "color": "#14b8a6"
    }
}