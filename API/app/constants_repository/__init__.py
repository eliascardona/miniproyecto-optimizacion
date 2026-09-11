from app.pydantic_schema.global_validator import safe_parse


class ConstantRepository:

    def __init__(self):
        self.repository = CustomerRepository()

    def create_customer(
        self,
        name: str,
    ):

        customer = Customer(
            id=None,
            name=self.cryptoService.encrypt(name),
        )

        row = self.repository.create(customer)

        return {
            "id": row["id"],
            "name": row["name"],
        }