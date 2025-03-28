from dataclasses import asdict, dataclass

ORDER_TYPE_PURCHASE = "Purchase"
ORDER_TYPE_CHANGE = "Change"
ORDER_TYPE_TERMINATION = "Termination"


@dataclass
class Context:
    order: dict

    @property
    def order_id(self):
        return self.order.get("id", None)

    @property
    def order_type(self):
        return self.order.get("type", None)

    @property
    def product_id(self):
        return self.order.get("product", {}).get("id", None)

    def is_purchase_order(self):
        return self.order["type"] == ORDER_TYPE_PURCHASE

    def is_change_order(self):
        return self.order["type"] == ORDER_TYPE_CHANGE

    def is_termination_order(self):
        return self.order["type"] == ORDER_TYPE_TERMINATION

    @classmethod
    def from_context(cls, context):
        base_data = asdict(context)
        return cls(**base_data)

    def __str__(self):
        return f"Context: {self.order.get("id", None)} {self.order.get("type", None)}"
