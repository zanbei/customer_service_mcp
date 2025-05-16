import json
import os
from typing import List, Dict, Optional

class OrderService:
    def __init__(self, data_file: str = "order_data.txt"):
        self.data_file = data_file
        self._initialize_data()
    
    def _initialize_data(self):
        """Initialize order data file if it doesn't exist."""
        if not os.path.exists(self.data_file):
            initial_data = [
                {"order_id": "123", "customer_name": "Alice Chen", "items": ["T-shirt", "Jeans"], "address": "Xicheng District, Beijing", "status": "Processing"},
                {"order_id": "456", "customer_name": "Bob Wang", "items": ["Dress", "Shoes"], "address": "Haidian District, Beijing", "status": "Shipped"},
                {"order_id": "789", "customer_name": "Charlie Liu", "items": ["Jacket", "Hat"], "address": "Dongcheng District, Beijing", "status": "Delivered"}
            ]
            self.save_order_data(initial_data)
    
    def get_order_data(self) -> List[Dict]:
        """Read order data from file."""
        try:
            with open(self.data_file, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error reading order data: {str(e)}")
            return []
    
    def save_order_data(self, order_data: List[Dict]) -> bool:
        """Save order data to file."""
        try:
            with open(self.data_file, 'w') as file:
                json.dump(order_data, file, indent=2)
            return True
        except Exception as e:
            print(f"Error saving order data: {str(e)}")
            return False
    
    def get_order_info(self, order_id: str) -> Optional[Dict]:
        """Get information for a specific order."""
        order_data = self.get_order_data()
        return next((order for order in order_data if order["order_id"] == order_id), None)
    
    def update_address(self, order_id: str, new_address: str) -> bool:
        """Update the address for a specific order."""
        order_data = self.get_order_data()
        
        for order in order_data:
            if order["order_id"] == order_id:
                order["address"] = new_address
                return self.save_order_data(order_data)
        
        return False
