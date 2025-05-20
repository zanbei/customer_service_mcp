from typing import Optional, List, Dict
from langchain.prompts import ChatPromptTemplate
from agents.base_agent import BaseAgent
from services.order_service import OrderService
from services.sop_service import SOPService

class OrderIssueAgent(BaseAgent):
    """Agent for handling order-related customer issues."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_service = OrderService()
        self.sop_service = SOPService()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a customer service agent for order issues.
Follow the decision tree below to handle customer inquiries:
{decision_tree}

Previous conversation:
{history}

Guidelines:
- PLEASE FOLLOW THE DECISION TREE AND DO NOT RESPOND RANDOMLY
- IF NOT SURE ABOUT THE OBJECT IN QUESTION, ASK FOR MORE DETAILS
- THIS IS INSTANT MESSAGING, KEEP RESPONSES SHORT AND CONCISE
- DO NOT USE PHRASES LIKE "BEST REGARDS" OR OTHER FORMAL CLOSINGS
- DO NOT RESPOND AS THE CUSTOMER"""),
            ("human", """Order Information:
{order_info}

Customer Question: {question}""")
        ])
    
    def _format_order_info(self, order_info: Optional[dict]) -> str:
        """Format order information for the prompt."""
        if not order_info:
            return "No specific order information provided."
        
        return (
            f"Order Details:\n"
            f"- Order ID: {order_info['order_id']}\n"
            f"- Customer: {order_info['customer_name']}\n"
            f"- Items: {', '.join(order_info['items'])}\n"
            f"- Status: {order_info['status']}\n"
            f"- Delivery Address: {order_info['address']}"
        )
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history."""
        if not history:
            return "No previous conversation."
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
    
    def process(self, user_input: str, conversation_id: Optional[str] = None, 
                order_id: Optional[str] = None, history: List[Dict[str, str]] = None, **kwargs) -> tuple[str, str]:
        """Process order-related customer inquiries.
        
        Args:
            user_input: The user's question
            conversation_id: Optional conversation ID for maintaining context
            order_id: Optional order ID if already known
            history: List of previous messages in the conversation
            
        Returns:
            tuple[str, str]: (response message, conversation_id)
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        # Get order information if order ID is provided
        order_info = None
        if order_id:
            order_info = self.order_service.get_order_info(order_id)
        
        # Prepare the chain
        chain = self.prompt | self.llm
        
        # Get response
        response = chain.invoke({
            "decision_tree": self.sop_service.order_decision_tree,
            "history": self._format_history(history or []),
            "order_info": self._format_order_info(order_info),
            "question": user_input
        })
        
        return response.content, conversation_id
