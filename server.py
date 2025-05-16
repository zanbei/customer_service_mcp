from mcp.server.fastmcp import FastMCP
import json
import uuid
from typing import Optional, Dict, Any

from main import CustomerServiceSystem

# Initialize FastMCP server
mcp = FastMCP("CustomerService")
system = CustomerServiceSystem()

@mcp.tool()
async def process_question(question: str, conversation_id: Optional[str] = None) -> str:
    """Process a customer service question and return a response."""
    try:
        response, new_conversation_id = system.process_question(question, conversation_id)
        result = {
            "response": response,
            "conversation_id": new_conversation_id
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "error": f"An error occurred: {str(e)}",
            "question": question
        })

@mcp.tool()
async def get_order_info(order_id: str) -> str:
    """Get information about a specific order."""
    try:
        order_info = system.order_service.get_order_info(order_id)
        if order_info:
            return json.dumps({
                "order": order_info
            }, ensure_ascii=False)
        return json.dumps({
            "error": f"Order {order_id} not found",
            "order_id": order_id
        })
    except Exception as e:
        return json.dumps({
            "error": f"An error occurred: {str(e)}",
            "order_id": order_id
        })

@mcp.tool()
async def update_order_address(order_id: str, new_address: str) -> str:
    """Update the delivery address for an order."""
    try:
        success = system.order_service.update_address(order_id, new_address)
        if success:
            updated_order = system.order_service.get_order_info(order_id)
            return json.dumps({
                "message": "Address updated successfully",
                "order": updated_order
            }, ensure_ascii=False)
        return json.dumps({
            "error": f"Failed to update address for order {order_id}",
            "order_id": order_id
        })
    except Exception as e:
        return json.dumps({
            "error": f"An error occurred: {str(e)}",
            "order_id": order_id
        })

@mcp.tool()
async def get_sop_tree(sop_type: str) -> str:
    """Get a specific SOP decision tree."""
    try:
        if sop_type.lower() == "order":
            return json.dumps({
                "decision_tree": system.sop_service.order_decision_tree
            }, ensure_ascii=False)
        elif sop_type.lower() == "logistics":
            return json.dumps({
                "decision_tree": system.sop_service.logistics_decision_tree
            }, ensure_ascii=False)
        return json.dumps({
            "error": f"Unknown SOP type: {sop_type}",
            "sop_type": sop_type
        })
    except Exception as e:
        return json.dumps({
            "error": f"An error occurred: {str(e)}",
            "sop_type": sop_type
        })

if __name__ == "__main__":
    mcp.run(transport="sse")
