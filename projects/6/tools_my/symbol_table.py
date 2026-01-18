class SymbolTable:
    """Symbol table for the Hack assembler.

    Maps symbols (labels / variables / predefined symbols) to 15-bit addresses.
    """

    def __init__(self):
        # Internal mapping: symbol -> address (int)
        self._table: dict[str, int] = {}

        # Predefined symbols (Hack platform specification)
        self._table.update({
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4,
            "SCREEN": 16384,
            "KBD": 24576,
        })

        # R0..R15
        for i in range(16):
            self._table[f"R{i}"] = i

    def addEntry(self, symbol: str, address: int) -> None:
        """Add/overwrite a symbol mapping."""
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("symbol must be a non-empty string")
        if not isinstance(address, int):
            raise ValueError("address must be int")
        if address < 0 or address > 32767:
            raise ValueError(f"address out of range (0..32767): {address}")
        self._table[symbol] = address

    def contains(self, symbol: str) -> bool:
        """Return True if the symbol exists in the table."""
        return symbol in self._table

    def getAddress(self, symbol: str) -> int:
        """Get the address for a symbol. Raises KeyError if missing."""
        if symbol not in self._table:
            raise KeyError(f"Symbol not found: {symbol}")
        return self._table[symbol]