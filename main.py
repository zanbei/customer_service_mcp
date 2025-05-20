import uuid
import json
import asyncio
import aioconsole
from typing import Optional, Dict, Any
from langchain_community.chat_models import BedrockChat
from langchain_mcp_adapters.client import MultiServerMCPClient
from agents.intent_recognition_agent import IntentRecognitionAgent
from agents.order_issue_agent import OrderIssueAgent
from agents.logistics_issue_agent import LogisticsIssueAgent
from services.order_service import OrderService
from services.sop_service import SOPService

class CustomerServiceSystem:
    """Main customer service system that coordinates agents and services."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0", region: str = "us-west-2"):
        """Initialize the customer service system with its agents and services."""
        # Initialize agents
        self.intent_agent = IntentRecognitionAgent(model_id=model_id, region=region)
        self.order_agent = OrderIssueAgent(model_id=model_id, region=region)
        self.logistics_agent = LogisticsIssueAgent(model_id=model_id, region=region)
        
        # Initialize services
        self.order_service = OrderService()
        self.sop_service = SOPService()
        
        # Store active conversations
        self.conversations: Dict[str, Dict[str, Any]] = {}
    
    def process_question(self, user_question: str, conversation_id: Optional[str] = None) -> tuple[str, str]:
        """Process a customer question through the multi-agent system.
        
        Args:
            user_question: The user's question
            conversation_id: Optional conversation ID for maintaining context
            
        Returns:
            tuple[str, str]: (response message, conversation_id)
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = {"order_id": None, "history": []}
        
        # Add user question to conversation history
        self.conversations[conversation_id]["history"].append({"role": "user", "content": user_question})
        
        # First layer: Intent recognition
        intent, _ = self.intent_agent.process(
            user_question,
            conversation_id,
            history=self.conversations[conversation_id]["history"]
        )
        print(f"Intent recognized: {intent}")
        # Extract order ID if present in the question
        import re
        order_id_match = re.search(r'order\s+(?:id\s+)?(?:number\s+)?(?:#\s*)?(\d+)', 
                                 user_question, re.IGNORECASE)
        if order_id_match:
            self.conversations[conversation_id]["order_id"] = order_id_match.group(1)
        
        # Second layer: Process based on intent
        if intent == "ORDER":
            response, _ = self.order_agent.process(
                user_question, 
                conversation_id,
                order_id=self.conversations[conversation_id].get("order_id"),
                history=self.conversations[conversation_id]["history"]
            )
        elif intent == "LOGISTICS":
            response, _ = self.logistics_agent.process(
                user_question,
                conversation_id,
                order_id=self.conversations[conversation_id].get("order_id"),
                history=self.conversations[conversation_id]["history"]
            )
        else:
            response = "I'm not sure if your question is about an order or logistics issue. Could you please provide more details?"
        
        # Add agent response to conversation history
        self.conversations[conversation_id]["history"].append({"role": "assistant", "content": response})
        
        return response, conversation_id

async def interactive_session():
    """Run an interactive session with the customer service system."""
    system = CustomerServiceSystem()
    conversation_id = None
    
    print("Welcome to Fashion E-commerce Customer Service!")
    print("You can ask questions about your orders or logistics.")
    print("Type 'exit' to end the conversation.")
    print("\nAvailable test orders: 123, 456, 789")
    print("-" * 50)
    
    client = MultiServerMCPClient(
        {
            "customer_service": {
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    )

    tools = await client.get_tools()
    process_question_tool = next(tool for tool in tools if tool.name == "process_question")

    while True:
        user_input = await aioconsole.ainput("\nCustomer: ")
        if user_input.lower() == 'exit':
            print("Thank you for using our customer service. Goodbye!")
            break
        
        try:
            result = await process_question_tool.arun({
                "question": user_input,
                "conversation_id": conversation_id
            })
            response_data = json.loads(result)
            print(f"\nAgent: {response_data['response']}")
            conversation_id = response_data['conversation_id']
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(interactive_session())
