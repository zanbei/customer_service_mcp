from typing import Optional, List, Dict
from langchain.prompts import ChatPromptTemplate
from agents.base_agent import BaseAgent

class IntentRecognitionAgent(BaseAgent):
    """Agent for recognizing customer intent from their questions."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent recognition system for fashion e-commerce customer service.
Your task is to analyze customer questions and determine if they are related to:
1. ORDER ISSUES (order status, modifications, problems, or payment)
2. LOGISTICS ISSUES (delivery address, shipping method, delivery problems)

Consider the conversation history provided to understand the context of the current question.

ONLY RESPOND WITH THE INTENT KEYWORD: ORDER or LOGISTICS
DO NOT RESPOND WITH A FULL SENTENCE."""),
            ("human", "Conversation history:\n{history}\n\nCurrent question: {question}")
        ])
    
    def process(self, user_input: str, conversation_id: Optional[str] = None, history: List[Dict[str, str]] = None, **kwargs) -> tuple[str, str]:
        """Process user input to determine their intent.
        
        Args:
            user_input: The user's question
            conversation_id: Optional conversation ID for maintaining context
            history: List of previous messages in the conversation
            
        Returns:
            tuple[str, str]: (intent type ("ORDER" or "LOGISTICS"), conversation_id)
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Format conversation history
        formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in (history or [])])
        
        # Get chain response
        chain = self.prompt | self.llm
        response = chain.invoke({"history": formatted_history, "question": user_input})
        intent = response.content.strip().upper()
        
        # Validate and normalize intent
        if "ORDER" in intent:
            intent = "ORDER"
        elif "LOGISTICS" in intent:
            intent = "LOGISTICS"
        else:
            intent = "UNKNOWN"
        
        return intent, conversation_id
