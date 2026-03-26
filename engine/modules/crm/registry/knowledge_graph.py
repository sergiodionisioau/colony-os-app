"""Revenue Knowledge Graph (R-KG) Manager."""

from collections import defaultdict
from typing import Dict, List
from .schemas import Identity, Entity, Signal, Relationship


class KnowledgeGraph:
    """Manages the relational data for revenue operations."""

    def __init__(self) -> None:
        self.identities: Dict[str, Identity] = {}
        self.entities: Dict[str, Entity] = {}
        self.signals: List[Signal] = []
        self.relationships: List[Relationship] = []
        # O(1) Indices
        self.signals_by_entity: Dict[str, List[Signal]] = defaultdict(list)
        self.relationships_by_target: Dict[str, List[Relationship]] = defaultdict(list)

    def upsert_identity(self, identity: Identity) -> None:
        """Adds or updates an identity in the graph."""
        self.identities[identity.uid] = identity

    def upsert_entity(self, entity: Entity) -> None:
        """Adds or updates an entity in the graph."""
        self.entities[entity.uid] = entity

    def add_signal(self, signal: Signal) -> None:
        """Adds a signal to the temporal store (Indexed)."""
        self.signals.append(signal)
        entity_uid = signal.payload.get("entity_uid")
        if entity_uid:
            self.signals_by_entity[entity_uid].append(signal)

    def add_relationship(self, relationship: Relationship) -> None:
        """Adds a relationship edge (Indexed)."""
        self.relationships.append(relationship)
        self.relationships_by_target[relationship.to_uid].append(relationship)

    def get_buying_committee(self, entity_uid: str) -> List[Identity]:
        """Returns all identities related to an entity (O(1) Lookup)."""
        uids = [
            r.from_uid
            for r in self.relationships_by_target.get(entity_uid, [])
            if r.type in ("WORKS_AT", "DECISION_MAKER_FOR")
        ]
        return [self.identities[uid] for uid in uids if uid in self.identities]

    def get_signal_history(self, target_uid: str) -> List[Signal]:
        """Returns signals associated with an entity (O(1) Lookup)."""
        return self.signals_by_entity.get(target_uid, [])
