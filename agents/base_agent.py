from abc import ABC, abstractmethod
from typing import Dict, Optional
from langchain_community.chat_models import BedrockChat
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage

class BaseAgent(ABC):
    """Base class for all customer service agents."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-west-2"):
        """Initialize the agent with a Bedrock model."""
        self.llm = BedrockChat(
            model_id=model_id,
            model_kwargs={"temperature": 0.7, "max_tokens": 2048},
            region_name=region
        )
        self.conversation_history: Dict[str, list[BaseMessage]] = {}
    
    def _get_history(self, conversation_id: str) -> list[BaseMessage]:
        """Get conversation history for a specific conversation."""
        return self.conversation_history.get(conversation_id, [])
    
    def _update_history(self, conversation_id: str, user_message: str, assistant_message: str):
        """Update conversation history with new messages."""
        if conversation_id not in self.conversation_history:
            self.conversation_history[conversation_id] = []
        
        self.conversation_history[conversation_id].extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ])
    
    @abstractmethod
    def process(self, user_input: str, conversation_id: Optional[str] = None, **kwargs) -> tuple[str, str]:
        """Process user input and return a response.
        
        Args:
            user_input: The user's message
            conversation_id: Optional conversation ID for maintaining context
            **kwargs: Additional arguments specific to each agent
            
        Returns:
            tuple[str, str]: (response message, conversation_id)
        """
        pass
