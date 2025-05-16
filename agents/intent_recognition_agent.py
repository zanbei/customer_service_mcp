from typing import Optional
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

ONLY RESPOND WITH THE INTENT KEYWORD: ORDER or LOGISTICS
DO NOT RESPOND WITH A FULL SENTENCE."""),
            ("user", "{question}")
        ])
    
    def process(self, user_input: str, conversation_id: Optional[str] = None, **kwargs) -> tuple[str, str]:
        """Process user input to determine their intent.
        
        Args:
            user_input: The user's question
            conversation_id: Optional conversation ID for maintaining context
            
        Returns:
            tuple[str, str]: (intent type ("ORDER" or "LOGISTICS"), conversation_id)
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Get chain response
        chain = self.prompt | self.llm
        response = chain.invoke({"question": user_input})
        intent = response.content.strip().upper()
        
        # Validate and normalize intent
        if "ORDER" in intent:
            intent = "ORDER"
        elif "LOGISTICS" in intent:
            intent = "LOGISTICS"
        else:
            intent = "UNKNOWN"
        
        # Update conversation history
        self._update_history(conversation_id, user_input, intent)
        
        return intent, conversation_id
