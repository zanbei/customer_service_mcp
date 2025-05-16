from typing import Dict, Any
from main import CustomerServiceSystem

class CustomerServiceMCP:
    """MCP server configuration for the customer service system."""
    
    def __init__(self):
        self.system = CustomerServiceSystem()
        self.conversations = {}
    
    def get_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define the tools provided by this MCP server."""
        return {
            "process_question": {
                "description": "Process a customer service question and return a response",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The customer's question"
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Optional conversation ID for maintaining context",
                            "optional": True
                        }
                    },
                    "required": ["question"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "The agent's response to the question"
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "The conversation ID for this interaction"
                        }
                    }
                },
                "handler": self.handle_process_question
            }
        }
    
    def get_resources(self) -> Dict[str, Dict[str, Any]]:
        """Define the resources provided by this MCP server."""
        return {
            "order_data": {
                "description": "Access to order data",
                "handler": self.handle_order_data_access
            },
            "sop_data": {
                "description": "Access to Standard Operating Procedures",
                "handler": self.handle_sop_data_access
            }
        }
    
    def handle_process_question(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the process_question tool."""
        question = args["question"]
        conversation_id = args.get("conversation_id")
        
        response, new_conversation_id = self.system.process_question(question, conversation_id)
        
        return {
            "response": response,
            "conversation_id": new_conversation_id
        }
    
    def handle_order_data_access(self, uri: str) -> Dict[str, Any]:
        """Handle access to order data."""
        if uri == "all":
            return {"orders": self.system.order_service.get_order_data()}
        
        order_id = uri
        order_info = self.system.order_service.get_order_info(order_id)
        if order_info:
            return {"order": order_info}
        return {"error": f"Order {order_id} not found"}
    
    def handle_sop_data_access(self, uri: str) -> Dict[str, Any]:
        """Handle access to SOP data."""
        if uri == "order":
            return {"decision_tree": self.system.sop_service.order_decision_tree}
        elif uri == "logistics":
            return {"decision_tree": self.system.sop_service.logistics_decision_tree}
        return {"error": f"Unknown SOP type: {uri}"}

# MCP server configuration
config = {
    "name": "customer-service",
    "version": "1.0.0",
    "description": "Customer service system for e-commerce platform",
    "server": CustomerServiceMCP()
}
