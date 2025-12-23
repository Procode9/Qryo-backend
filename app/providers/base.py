class QuantumProvider:
    name = "base"

    def run(self, payload: dict) -> dict:
        raise NotImplementedError
