"""
SpeakerMem-R1: Five-Layer Speaker-Indexed Memory Data Structure

Implements the M = {M_core^s, M_episodic^s, M_profile^s}_{s∈S} ∪ {M_interact, M_insight}
architecture from §3.2 of the paper draft.

Each entry tracks: (owner, content, audience_set, layer, creation_turn)
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class MemoryLayer(str, Enum):
    CORE = "core"           # M_core^s: persistent speaker facts
    EPISODIC = "episodic"   # M_episodic^s: time-indexed episodes
    PROFILE = "profile"     # M_profile^s: communication style/preferences
    INTERACT = "interact"   # M_interact: cross-speaker relationships (group-level)
    INSIGHT = "insight"     # M_insight: high-level meta-knowledge (group-level)


@dataclass
class MemoryEntry:
    """
    A single memory fact.

    Fields match the formal definition in §3.2:
      e ∈ M_core^s is tuple (s_owner, content, A_e, l_e, t_e)
    """
    entry_id: str
    owner: str                          # s_owner: speaker who owns this fact
    content: str                        # the fact text
    audience: list[str]                 # A_e: speakers who can access this fact
    layer: MemoryLayer                  # l_e: which memory layer
    creation_turn: int                  # t_e: turn index when created
    last_updated_turn: int = -1
    is_suppressed: bool = False         # SUPPRESS action applied
    suppress_lambda: float = 0.0        # decay factor if suppressed (0 = deleted)
    source_utterance: str = ""          # original utterance that triggered this entry


    def is_accessible_by(self, requester: str) -> bool:
        """Check if requester is in the audience set for this entry."""
        if self.is_suppressed and self.suppress_lambda == 0.0:
            return False
        return requester in self.audience or self.audience == ["*"]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["layer"] = self.layer.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        d = dict(d)
        d["layer"] = MemoryLayer(d["layer"])
        return cls(**d)


class SpeakerAwareMemory:
    """
    Five-layer speaker-indexed memory for multi-party conversations.

    Usage:
        mem = SpeakerAwareMemory(speakers=["Alice", "Bob", "Carol"])
        mem.write("Alice", "Alice works at ByteDance", audience=["Alice", "Bob", "Carol"],
                  layer=MemoryLayer.CORE, turn=1)
        facts = mem.read("Alice", reader="Bob")  # returns Alice's facts accessible to Bob
        delta = mem.get_delta(since_turn=5)       # get changes since turn 5
    """

    def __init__(self, speakers: list[str], group_id: str = "default"):
        self.speakers = speakers
        self.group_id = group_id
        self._entries: dict[str, MemoryEntry] = {}  # entry_id → MemoryEntry
        self._turn_index: dict[int, list[str]] = {}  # turn → [entry_ids modified]
        self._counter = 0

    # ------------------------------------------------------------------
    # Core CRUD operations (correspond to action space in §3.3)
    # ------------------------------------------------------------------

    def write(
        self,
        owner: str,
        content: str,
        audience: list[str],
        layer: MemoryLayer,
        turn: int,
        source_utterance: str = "",
    ) -> str:
        """WRITE(c, s, A, l) action: add new fact."""
        entry_id = f"{self.group_id}_{owner}_{self._counter:04d}"
        self._counter += 1
        entry = MemoryEntry(
            entry_id=entry_id,
            owner=owner,
            content=content,
            audience=audience,
            layer=layer,
            creation_turn=turn,
            last_updated_turn=turn,
            source_utterance=source_utterance,
        )
        self._entries[entry_id] = entry
        self._track_turn(turn, entry_id)
        return entry_id

    def update(self, entry_id: str, new_content: str, turn: int) -> bool:
        """UPDATE(e, c) action: modify existing entry content."""
        if entry_id not in self._entries:
            return False
        self._entries[entry_id].content = new_content
        self._entries[entry_id].last_updated_turn = turn
        self._track_turn(turn, entry_id)
        return True

    def delete(self, entry_id: str, turn: int) -> bool:
        """DELETE(e) action: hard remove entry."""
        if entry_id not in self._entries:
            return False
        self._entries.pop(entry_id)
        return True

    def suppress(self, entry_id: str, lambda_decay: float, turn: int) -> bool:
        """SUPPRESS(e, λ) action: soft decay/hide entry (for forgetting or privacy)."""
        if entry_id not in self._entries:
            return False
        self._entries[entry_id].is_suppressed = True
        self._entries[entry_id].suppress_lambda = lambda_decay
        self._entries[entry_id].last_updated_turn = turn
        return True

    def summary(self, entry_ids: list[str], target_layer: MemoryLayer, owner: str, turn: int) -> str:
        """SUMMARY(E, l) action: compress multiple entries into a single summary entry."""
        contents = [self._entries[eid].content for eid in entry_ids if eid in self._entries]
        summarized = " | ".join(contents)  # placeholder; real impl uses LLM
        new_id = self.write(owner, f"[SUMMARY] {summarized}", ["*"], target_layer, turn)
        for eid in entry_ids:
            self.delete(eid, turn)
        return new_id

    def promote(self, entry_id: str, new_layer: MemoryLayer, turn: int) -> bool:
        """PROMOTE(e) action: move entry to higher-priority layer."""
        if entry_id not in self._entries:
            return False
        self._entries[entry_id].layer = new_layer
        self._entries[entry_id].last_updated_turn = turn
        return True

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def _track_turn(self, turn: int, entry_id: str) -> None:
        if turn not in self._turn_index:
            self._turn_index[turn] = []
        if entry_id not in self._turn_index[turn]:
            self._turn_index[turn].append(entry_id)

    def read(
        self,
        owner: str,
        reader: str,
        layer: Optional[MemoryLayer] = None,
        include_group_layers: bool = True,
    ) -> list[MemoryEntry]:
        """
        READ(s, s') action: retrieve owner's facts accessible to reader.

        Returns entries where:
          - entry.owner == owner (or group-level layers if include_group_layers)
          - entry.is_accessible_by(reader)
          - optional: filter by layer
        """
        results = []
        for entry in self._entries.values():
            if entry.is_suppressed and entry.suppress_lambda == 0.0:
                continue
            # Per-speaker layers: match owner
            if entry.layer in (MemoryLayer.CORE, MemoryLayer.EPISODIC, MemoryLayer.PROFILE):
                if entry.owner != owner:
                    continue
            # Group-level layers: always include if flag set
            elif not include_group_layers:
                continue

            if layer is not None and entry.layer != layer:
                continue

            if entry.is_accessible_by(reader):
                results.append(entry)

        return sorted(results, key=lambda e: e.creation_turn)

    def read_all_for_reader(self, reader: str) -> list[MemoryEntry]:
        """Return all entries accessible to a given reader."""
        return [e for e in self._entries.values() if e.is_accessible_by(reader)]

    # ------------------------------------------------------------------
    # Delta computation (for SpeakerLevenshtein reward)
    # ------------------------------------------------------------------

    def get_speaker_state(self, speaker: str) -> list[str]:
        """
        Return list of fact strings for a given speaker.
        Used as input to SpeakerLevenshteinReward.compute().
        """
        entries = [
            e for e in self._entries.values()
            if e.owner == speaker and not (e.is_suppressed and e.suppress_lambda == 0.0)
        ]
        return [e.content for e in entries]

    def get_all_states(self) -> dict[str, list[str]]:
        """Return {speaker: [fact_strings]} for all speakers."""
        return {s: self.get_speaker_state(s) for s in self.speakers}

    def get_delta(self, since_turn: int) -> dict[str, list[str]]:
        """
        Return entries modified since a given turn (used for process reward computation).
        Returns {speaker: [new_or_updated_content]}.
        """
        delta: dict[str, list[str]] = {s: [] for s in self.speakers}
        delta["group"] = []
        for entry in self._entries.values():
            if entry.last_updated_turn >= since_turn:
                if entry.layer in (MemoryLayer.CORE, MemoryLayer.EPISODIC, MemoryLayer.PROFILE):
                    delta[entry.owner].append(entry.content)
                else:
                    delta["group"].append(entry.content)
        return delta

    # ------------------------------------------------------------------
    # Attribution error detection (for R_leak reward)
    # ------------------------------------------------------------------

    def get_attribution_errors(self, ground_truth_memory: "SpeakerAwareMemory") -> dict:
        """
        Compare this memory against ground truth to compute attribution errors.
        An attribution error = fact with wrong owner assignment.
        Used internally to compute R_leak.
        """
        errors = {s: [] for s in self.speakers}
        for entry in self._entries.values():
            if entry.layer not in (MemoryLayer.CORE, MemoryLayer.EPISODIC):
                continue
            # Check if this fact belongs to a different speaker in GT
            for gt_entry in ground_truth_memory._entries.values():
                if gt_entry.content.strip().lower() == entry.content.strip().lower():
                    if gt_entry.owner != entry.owner:
                        errors[entry.owner].append({
                            "fact": entry.content,
                            "predicted_owner": entry.owner,
                            "true_owner": gt_entry.owner,
                        })
        return errors

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "group_id": self.group_id,
            "speakers": self.speakers,
            "entries": {eid: e.to_dict() for eid, e in self._entries.items()},
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "SpeakerAwareMemory":
        mem = cls(speakers=d["speakers"], group_id=d["group_id"])
        for eid, edict in d["entries"].items():
            mem._entries[eid] = MemoryEntry.from_dict(edict)
        return mem

    def __repr__(self) -> str:
        counts = {s: len(self.get_speaker_state(s)) for s in self.speakers}
        return f"SpeakerAwareMemory(group={self.group_id}, facts_per_speaker={counts})"


# ------------------------------------------------------------------
# Quick smoke test
# ------------------------------------------------------------------

if __name__ == "__main__":
    speakers = ["Alice", "Bob", "Carol"]
    mem = SpeakerAwareMemory(speakers=speakers, group_id="test_group")

    # Turn 1: Alice mentions her job
    mem.write("Alice", "Alice works at ByteDance", audience=speakers,
              layer=MemoryLayer.CORE, turn=1, source_utterance="I work at ByteDance.")

    # Turn 3: Bob mentions he prefers formal English
    mem.write("Bob", "Bob uses formal English", audience=speakers,
              layer=MemoryLayer.PROFILE, turn=3, source_utterance="I prefer writing formally.")

    # Turn 5: Carol says something private to Alice only
    mem.write("Carol", "Carol is considering switching to a startup",
              audience=["Carol", "Alice"],
              layer=MemoryLayer.CORE, turn=5,
              source_utterance="Alice, just between us, I'm thinking of joining a startup.")

    # Turn 7: Alice updates her job (she moved)
    mem.write("Alice", "Alice moved to Tencent (from ByteDance)",
              audience=speakers, layer=MemoryLayer.EPISODIC, turn=7,
              source_utterance="I just got hired by Tencent!")

    # Group-level: Alice and Bob have collaborated
    mem.write("Alice", "Alice and Bob previously collaborated on a project",
              audience=speakers, layer=MemoryLayer.INTERACT, turn=8)

    print("=== Memory state ===")
    print(mem)
    print()

    print("=== Alice's facts (read by Bob) ===")
    for e in mem.read("Alice", reader="Bob"):
        print(f"  [{e.layer.value}] {e.content}")
    print()

    print("=== Carol's facts (read by Carol) ===")
    for e in mem.read("Carol", reader="Carol"):
        print(f"  [{e.layer.value}] {e.content}")
    print()

    print("=== Carol's facts (read by Bob — should see nothing private) ===")
    for e in mem.read("Carol", reader="Bob"):
        print(f"  [{e.layer.value}] {e.content}")
    print("  (empty = correct, Carol's startup fact is private to Carol+Alice)")
    print()

    print("=== Full state as dict (all speakers) ===")
    all_states = mem.get_all_states()
    for spk, facts in all_states.items():
        print(f"  {spk}: {facts}")
    print()

    print("=== Delta since turn 6 ===")
    delta = mem.get_delta(since_turn=6)
    for spk, facts in delta.items():
        if facts:
            print(f"  {spk}: {facts}")
    print()

    # Test serialization round-trip
    serialized = mem.to_json()
    mem2 = SpeakerAwareMemory.from_dict(json.loads(serialized))
    assert mem2.get_all_states() == mem.get_all_states(), "Serialization round-trip failed!"
    print("✅ Serialization round-trip: PASS")
    print()

    # Suppress test
    carol_entries = [e for e in mem._entries.values() if e.owner == "Carol"]
    if carol_entries:
        mem.suppress(carol_entries[0].entry_id, lambda_decay=0.0, turn=9)
        print("=== After SUPPRESS Carol's first entry ===")
        remaining = mem.read("Carol", reader="Carol")
        print(f"  Carol's accessible facts: {[e.content for e in remaining]}")
    print()
    print("All tests passed ✅")
