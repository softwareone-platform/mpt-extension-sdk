from dataclasses import asdict, dataclass

ORDER_TYPE_PURCHASE = "Purchase"
ORDER_TYPE_CHANGE = "Change"
ORDER_TYPE_TERMINATION = "Termination"


@dataclass
class Context:
    """Represents the context for an order."""
    order: dict

    @property
    def order_id(self):
        """Return the order ID."""
        return self.order.get("id", None)

    @property
    def order_type(self):
        """Return the order type."""
        return self.order.get("type", None)

    @property
    def product_id(self):
        """Return the product ID."""
        return self.order.get("product", {}).get("id", None)

    def is_purchase_order(self):
        """Check if the order is a purchase order."""
        return self.order["type"] == ORDER_TYPE_PURCHASE

    def is_change_order(self):
        """Check if the order is a change order."""
        return self.order["type"] == ORDER_TYPE_CHANGE

    def is_termination_order(self):
        """Check if the order is a termination order."""
        return self.order["type"] == ORDER_TYPE_TERMINATION

    @classmethod
    def from_context(cls, context):
        """Create a new Context instance from an existing one."""
        base_data = asdict(context)
        return cls(**base_data)

    def __str__(self):
        order_id = self.order.get("id", None)
        order_type = self.order.get("type", None)
        return f"Context: {order_id} {order_type}"
