class SOPService:
    """Service for managing Standard Operating Procedures (SOP) decision trees."""
    
    @property
    def order_decision_tree(self) -> str:
        return """
# Order Issues Decision Tree
1. Order Status
   1.1. Where is my order? -> Check order status using order ID
2. Order Modification
   2.1. Can I modify/delete my order? -> Check if order is still processing
   2.3. I want to add items to my order -> Check if order is still processing
"""

    @property
    def logistics_decision_tree(self) -> str:
        return """
# Logistics Issues Decision Tree
1. Package Location Inquiries
   1.2. Package exceeds estimated delivery time
      1.2.1. Check package tracking on carrier website
         1.2.1.1. Exceeds ETA by <7 days -> Suggest waiting 2-3 more days
         1.2.1.2. Exceeds ETA by >7 days with tracking updates -> Suggest waiting 2-3 days and contacting carrier
            1.2.1.2.1. Customer unwilling to wait -> Offer 100 points compensation
            1.2.1.2.2. Customer highly upset -> Offer 100% store credit (final offer: 100% cash refund)
         1.2.1.3. Exceeds ETA by >7 days with no tracking updates -> Offer 100% store credit or resend options
   1.3. Tracking shows no updates for 4+ days
      1.3.1. Still within ETA -> Escalate to logistics team for investigation
      1.3.2. Exceeds ETA -> Follow "Package exceeds estimated delivery time" process
   1.4. Failed delivery attempts
      1.4.1. Middle East regions -> Confirm delivery info, request GPS link, register for redelivery
      1.4.2. Other regions -> Confirm delivery info, suggest keeping phone available, provide carrier contact
   1.5. Package returned to sender
      1.5.1. Delivery address matches system -> Prioritize reshipment or offer 100% store credit
      1.5.2. Delivery address incorrect -> Offer 50-100% store credit or resend options

2. Delivery Address
   2.1. change delivery address -> Update address if order not shipped
   2.3. Address verification -> Confirm address details

3. Package Marked as Delivered but Not Received
   3.1. Check for whole package not received or missing items
      3.1.1. Share with customer and verify address
      3.3.1. First-time customer
         3.3.1.1. Address correct -> Offer resend or 100% cash refund
         3.3.1.2. Address incorrect -> Offer 50% store credit (final: resend or 100% cash refund)
      3.3.2. Returning customer
         3.3.2.1. Address correct & order <$200 -> Offer 100% store credit
         3.3.2.2. Address incorrect & order <$200 -> Offer 50% store credit
         3.3.2.3. Order >$200 -> Escalate to team lead

5. Package Awaiting Pickup
   5.1. Verify if customer received pickup notification
   5.2. Provide carrier contact info for pickup details

6. Combined Packages with Missing Items
   6.1. Offer options:
      6.1.1. Arrange reshipment
      6.1.2. Provide 100% store credit (6-month validity)
      6.1.3. If customer rejects both -> Offer 100% cash refund

Note: Special considerations
- Do not offer resend if customer already paid customs duty
- For BNPL payment methods (Klarna/Afterpay), emphasize store credit is not real money
- For orders >$200 with special circumstances, escalate to team lead
"""
