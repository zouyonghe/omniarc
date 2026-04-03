from dataclasses import dataclass, field


@dataclass(slots=True)
class CapabilitySet:
    values: set[str] = field(default_factory=set)

    def supports(self, name: str) -> bool:
        return name in self.values
