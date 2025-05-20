# E-commerce Customer Service System with LangChain and MCP

A modular customer service system that uses LangChain and the Model Context Protocol (MCP) to handle e-commerce customer inquiries about orders and logistics.

## Project Structure

```
customer_service_mcp/
├── agents/
│   ├── base_agent.py         # Base agent class with common functionality
│   ├── intent_recognition_agent.py  # Agent for determining customer intent
│   ├── order_issue_agent.py  # Agent for handling order-related issues
│   └── logistics_issue_agent.py  # Agent for handling logistics issues
├── services/
│   ├── order_service.py      # Service for managing order data
│   └── sop_service.py        # Service for managing SOP decision trees
├── config/
│   └── mcp_config.py         # MCP server configuration
├── main.py                   # Main application entry point
├── requirements.txt          # Project dependencies
├── server.py                 # MCP server implementation
└── README.md                 # Project documentation
```

## Features

- Multi-agent system for handling customer inquiries
- Intent recognition to route questions to appropriate agents
- Order management with persistent storage
- Standard Operating Procedures (SOP) with decision trees
- Conversation history tracking
- MCP server integration for external tool access

## Setup

1. Create and activate a Python virtual environment:
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Configure AWS credentials for Bedrock:
   - Set up your AWS credentials in `~/.aws/credentials` or use environment variables
   - Ensure you have access to the Bedrock service in your AWS region

3. Run the interactive session:
   ```bash
   python main.py
   ```

## MCP Server Usage

The system is implemented as an MCP server using FastMCP, providing the following tools:

### Tools

1. `process_question`: Process customer service inquiries
   - Input:
     - question (str, required): The customer's question
     - conversation_id (str, optional): ID for maintaining conversation context
   - Output: JSON response with message and conversation ID

2. `get_order_info`: Get information about a specific order
   - Input:
     - order_id (str, required): The ID of the order to look up
   - Output: JSON response with order details or error message

3. `update_order_address`: Update an order's delivery address
   - Input:
     - order_id (str, required): The ID of the order to update
     - new_address (str, required): The new delivery address
   - Output: JSON response with updated order details or error message

4. `get_sop_tree`: Get a specific SOP decision tree
   - Input:
     - sop_type (str, required): Type of SOP ("order" or "logistics")
   - Output: JSON response with decision tree content or error message

### Running the Server

#### Quick Start (Unix/Linux/MacOS)
Simply run the provided startup script:
```bash
./start_server.sh
```
This script will:
1. Create a Python virtual environment if it doesn't exist
2. Activate the virtual environment
3. Install dependencies if needed
4. Start the MCP server

#### Manual Setup (Windows or Alternative)
1. Create and activate virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Windows:
   venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Start the MCP server:
   ```bash
   python server.py
   ```

The server will start in SSE (Server-Sent Events) transport mode, making it compatible with various MCP clients. Once started, the server will expose the following endpoints:
- Process customer inquiries
- Get order information
- Update order addresses
- Access SOP decision trees

## Example Usage

```python
from main import CustomerServiceSystem

# Create system instance
system = CustomerServiceSystem()

# Process a question
response, conv_id = system.process_question("What's the status of order #123?")
print(f"Agent: {response}")
```

## Test Orders

The system comes with pre-configured test orders:
- Order #123: Processing
- Order #456: Shipped
- Order #789: Delivered

## Decision Trees

The system uses decision trees to handle:
- Order Issues: Status inquiries, modifications
- Logistics Issues: Delivery tracking, address changes, missing packages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
