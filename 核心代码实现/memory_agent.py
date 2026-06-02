"""
SpeakerMem-R1: Memory Agent Pipeline

Implements the three-agent memory management system from §3.7:
  - ConstructionAgent: ADD/UPDATE/DELETE/SUMMARY/PROMOTE/SUPPRESS/NOOP
  - RetrievalAgent: READ(s, s') with speaker-conditioned query
  - AnswerAgent: speaker-aware answer generation

All three agents share a single Qwen3-8B backbone (co-learning per Memory-R2 §3.7).
Role-specific prompts differentiate agent behavior at inference time.

During training, each agent is called in sequence within a GRPO rollout:
  1. ConstructionAgent processes new turns → updates SpeakerAwareMemory
  2. RetrievalAgent reads relevant facts for the query
  3. AnswerAgent generates the final answer

Usage (inference):
    agent = SpeakerMemAgent(model_name="Qwen/Qwen3-8B", device="cuda")
    result = agent.forward(
        conversation=conv_turns,
        query={"asker": "Alice", "target": "Bob", "text": "Where does Bob work?"},
        speakers=["Alice", "Bob", "Carol"]
    )
    print(result["answer"])  # "Bob works at ByteDance"
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Optional
from speaker_aware_memory import SpeakerAwareMemory, MemoryLayer


# ------------------------------------------------------------------
# Prompt Templates (role-specific, per co-learning design in §3.7)
# ------------------------------------------------------------------

CONSTRUCTION_SYSTEM_PROMPT = """You are a multi-party conversation memory construction agent.
Your task: analyze a new conversation turn and decide what memory operations to perform.

You MUST identify the speaker of each statement and attribute facts ONLY to their source speaker.
Memory layers:
- core: persistent personal facts (job, location, preferences)
- episodic: time-indexed events (what happened at turn N)
- profile: communication style, personality traits
- interact: cross-speaker relationships or events
- insight: high-level group meta-knowledge

Output one or more of these actions in JSON format:
{
  "actions": [
    {"type": "WRITE", "owner": "Alice", "content": "Alice works at ByteDance",
     "audience": ["Alice", "Bob", "Carol"], "layer": "core"},
    {"type": "UPDATE", "entry_id": "...", "content": "Alice now works at Tencent"},
    {"type": "DELETE", "entry_id": "..."},
    {"type": "SUPPRESS", "entry_id": "...", "lambda": 0.0},
    {"type": "NOOP"}
  ]
}

CRITICAL RULES:
1. NEVER merge facts from different speakers into the same entry
2. If two speakers mention the same entity, create SEPARATE entries with different owners
3. Private information shared between specific speakers should have a restricted audience list
4. Use UPDATE (not WRITE) if a speaker contradicts or updates a previously recorded fact
"""

RETRIEVAL_SYSTEM_PROMPT = """You are a multi-party conversation memory retrieval agent.
Your task: given a query from a specific asker about a specific target, retrieve the most relevant memory facts.

The query format: (asker, target, question_text)
- asker: who is asking the question
- target: who/what the question is about
- question_text: the natural language question

You should:
1. First retrieve facts from target's per-speaker memory (core, episodic, profile)
2. Then check cross-speaker relationships (interact layer)
3. Filter based on asker's access permissions (audience field)
4. Return the top-k most relevant facts for answering the query

Output:
{
  "retrieved_facts": [
    {"fact": "Alice works at ByteDance", "layer": "core", "owner": "Alice", "relevance": 0.95},
    ...
  ],
  "reasoning": "Why these facts are relevant to the query"
}
"""

ANSWER_SYSTEM_PROMPT = """You are a multi-party conversation memory answering agent.
Your task: generate a speaker-aware answer using retrieved memory facts.

You must:
1. Answer based ONLY on the retrieved facts (no hallucination)
2. Correctly attribute information to its source speaker
3. Respect audience restrictions (don't reveal info the asker shouldn't know)
4. If the answer cannot be determined from memory, say "I don't have that information"

Output:
{
  "answer": "Based on my memory, Bob mentioned he works at Tencent in session 3.",
  "confidence": 0.9,
  "requires_clarification": false
}
"""


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class ConversationTurn:
    speaker: str
    text: str
    turn_id: int
    session_id: int = 1


@dataclass
class MemoryQuery:
    asker: str
    target: str       # who/what the question is about
    text: str         # question text
    query_id: str = ""


@dataclass
class AgentOutput:
    actions: list[dict]             # construction actions
    retrieved_facts: list[dict]     # retrieval results
    answer: str                     # final answer
    confidence: float
    raw_construction: str = ""
    raw_retrieval: str = ""
    raw_answer: str = ""


# ------------------------------------------------------------------
# Parsing utilities
# ------------------------------------------------------------------

def parse_json_output(text: str, required_key: str) -> dict:
    """Extract and parse JSON from LLM output, handling markdown code blocks."""
    # Strip markdown code blocks if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()

    try:
        data = json.loads(text)
        if required_key not in data:
            return {required_key: []}
        return data
    except json.JSONDecodeError:
        # Try to extract JSON object
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {required_key: []}


def format_memory_for_retrieval(memory: SpeakerAwareMemory, reader: str) -> str:
    """Format memory state as text for the retrieval agent's context."""
    lines = ["=== Current Memory State ==="]
    for speaker in memory.speakers:
        facts = memory.read(speaker, reader=reader)
        if facts:
            lines.append(f"\n[{speaker}'s memory]")
            for f in facts:
                lines.append(f"  [{f.layer.value}] {f.content} (turn {f.creation_turn})")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Main Agent Class
# ------------------------------------------------------------------

class SpeakerMemAgent:
    """
    Complete SpeakerMem-R1 memory agent pipeline.

    Architecture: single shared backbone (Qwen3-8B) with role-specific prompts.
    This implements the co-learning design from §3.7 (inspired by Memory-R2).

    In training mode: each forward() call generates a rollout for GRPO.
    In inference mode: each forward() call answers a query given conversation history.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-8B",
        device: str = "cpu",
        use_mock_llm: bool = False,    # True for testing without GPU
        max_new_tokens: int = 512,
    ):
        self.model_name = model_name
        self.device = device
        self.use_mock_llm = use_mock_llm
        self.max_new_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None

        if not use_mock_llm:
            self._load_model()

    def _load_model(self):
        """Load Qwen3-8B backbone. Only called when use_mock_llm=False."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16,
                device_map=self.device,
            )
        except ImportError:
            raise RuntimeError("transformers not installed. Run: pip install transformers torch")

    def _call_llm(self, system_prompt: str, user_content: str) -> str:
        """Call the backbone LLM with role-specific system prompt."""
        if self.use_mock_llm:
            return self._mock_llm_response(system_prompt, user_content)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self.device)
        import torch
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=0.7,
                do_sample=True,
            )
        output_text = self._tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
        return output_text.strip()

    def _mock_llm_response(self, system_prompt: str, user_content: str) -> str:
        """Mock LLM for testing pipeline without GPU. Returns minimal valid JSON."""
        if "construction" in system_prompt.lower() or "WRITE" in system_prompt:
            return json.dumps({
                "actions": [
                    {"type": "WRITE", "owner": "Alice", "content": "Alice mentioned something",
                     "audience": ["*"], "layer": "core"}
                ]
            })
        elif "retrieval" in system_prompt.lower() or "retrieved_facts" in system_prompt:
            return json.dumps({
                "retrieved_facts": [
                    {"fact": "Mock fact about target", "layer": "core",
                     "owner": "Bob", "relevance": 0.8}
                ],
                "reasoning": "Mock retrieval for testing"
            })
        else:
            return json.dumps({
                "answer": "Mock answer for testing purposes.",
                "confidence": 0.7,
                "requires_clarification": False
            })

    # ------------------------------------------------------------------
    # Three-stage pipeline
    # ------------------------------------------------------------------

    def construct(
        self,
        turn: ConversationTurn,
        memory: SpeakerAwareMemory,
        conversation_context: list[ConversationTurn],
    ) -> list[dict]:
        """
        Stage 1: ConstructionAgent
        Processes a new turn and returns a list of memory actions.
        """
        context_text = "\n".join(
            f"[Turn {t.turn_id}, {t.speaker}]: {t.text}"
            for t in conversation_context[-5:]  # last 5 turns for context
        )
        current_memory_summary = ", ".join(
            f"{s}: {len(memory.get_speaker_state(s))} facts"
            for s in memory.speakers
        )

        user_content = f"""SPEAKERS: {memory.speakers}
RECENT CONTEXT:
{context_text}

NEW TURN to process:
[Turn {turn.turn_id}, {turn.speaker}]: {turn.text}

CURRENT MEMORY: {current_memory_summary}

What memory operations should be performed?"""

        raw_output = self._call_llm(CONSTRUCTION_SYSTEM_PROMPT, user_content)
        parsed = parse_json_output(raw_output, "actions")
        actions = parsed.get("actions", [{"type": "NOOP"}])

        # Apply actions to memory
        for action in actions:
            self._apply_action(action, memory, turn.turn_id)

        return actions

    def retrieve(
        self,
        query: MemoryQuery,
        memory: SpeakerAwareMemory,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Stage 2: RetrievalAgent
        Retrieves relevant facts for the query, respecting access permissions.
        """
        memory_text = format_memory_for_retrieval(memory, reader=query.asker)

        user_content = f"""QUERY:
  Asker: {query.asker}
  About: {query.target}
  Question: {query.text}

AVAILABLE MEMORY (accessible to {query.asker}):
{memory_text}

Retrieve the top-{top_k} most relevant facts for answering this query."""

        raw_output = self._call_llm(RETRIEVAL_SYSTEM_PROMPT, user_content)
        parsed = parse_json_output(raw_output, "retrieved_facts")
        return parsed.get("retrieved_facts", [])

    def answer(
        self,
        query: MemoryQuery,
        retrieved_facts: list[dict],
    ) -> dict:
        """
        Stage 3: AnswerAgent
        Generates speaker-aware answer from retrieved facts.
        """
        facts_text = "\n".join(
            f"- [{f.get('layer', 'core')}] {f.get('owner', '?')}: {f.get('fact', '')}"
            for f in retrieved_facts
        )

        user_content = f"""QUERY:
  Asker: {query.asker}
  About: {query.target}
  Question: {query.text}

RETRIEVED FACTS:
{facts_text if facts_text else "(no relevant facts found)"}

Generate a speaker-aware answer. Remember: only use information from the retrieved facts."""

        raw_output = self._call_llm(ANSWER_SYSTEM_PROMPT, user_content)
        parsed = parse_json_output(raw_output, "answer")
        return {
            "answer": parsed.get("answer", "I don't have that information."),
            "confidence": parsed.get("confidence", 0.5),
            "raw": raw_output,
        }

    def forward(
        self,
        conversation: list[ConversationTurn],
        query: MemoryQuery,
        speakers: list[str],
        group_id: str = "session",
    ) -> AgentOutput:
        """
        Full pipeline: process conversation → build memory → retrieve → answer.
        Used for both training rollouts and inference.
        """
        memory = SpeakerAwareMemory(speakers=speakers, group_id=group_id)

        all_actions = []
        for i, turn in enumerate(conversation):
            context = conversation[max(0, i - 5):i]
            actions = self.construct(turn, memory, context)
            all_actions.extend(actions)

        retrieved = self.retrieve(query, memory)
        answer_result = self.answer(query, retrieved)

        return AgentOutput(
            actions=all_actions,
            retrieved_facts=retrieved,
            answer=answer_result["answer"],
            confidence=answer_result["confidence"],
        )

    def _apply_action(self, action: dict, memory: SpeakerAwareMemory, turn_id: int) -> None:
        """Apply a single construction action to memory."""
        action_type = action.get("type", "NOOP")

        if action_type == "WRITE":
            layer_str = action.get("layer", "core")
            try:
                layer = MemoryLayer(layer_str)
            except ValueError:
                layer = MemoryLayer.CORE
            audience = action.get("audience", memory.speakers)
            if audience == ["*"] or "*" in audience:
                audience = memory.speakers[:]
            memory.write(
                owner=action.get("owner", memory.speakers[0]),
                content=action.get("content", ""),
                audience=audience,
                layer=layer,
                turn=turn_id,
            )

        elif action_type == "UPDATE":
            entry_id = action.get("entry_id", "")
            content = action.get("content", "")
            if entry_id and content:
                memory.update(entry_id, content, turn_id)

        elif action_type == "DELETE":
            entry_id = action.get("entry_id", "")
            if entry_id:
                memory.delete(entry_id, turn_id)

        elif action_type == "SUPPRESS":
            entry_id = action.get("entry_id", "")
            lam = float(action.get("lambda", 0.0))
            if entry_id:
                memory.suppress(entry_id, lam, turn_id)

        elif action_type == "NOOP":
            pass


# ------------------------------------------------------------------
# Quick smoke test (mock LLM)
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SpeakerMemAgent Pipeline Smoke Test ===\n")

    agent = SpeakerMemAgent(use_mock_llm=True)

    speakers = ["Alice", "Bob", "Carol"]
    conversation = [
        ConversationTurn("Alice", "I just started working at ByteDance!", 1),
        ConversationTurn("Bob", "That's great! I've been at Tencent for 2 years.", 2),
        ConversationTurn("Carol", "I'm thinking of joining a startup.", 3),
        ConversationTurn("Alice", "Carol, which startup are you considering?", 4),
        ConversationTurn("Carol", "It's a small AI company, but let's keep it between us.", 5),
        ConversationTurn("Bob", "Alice, I heard ByteDance has great perks!", 6),
    ]

    query = MemoryQuery(
        asker="Alice",
        target="Carol",
        text="What is Carol planning to do with her career?",
        query_id="q001",
    )

    print("Processing conversation through 3-stage pipeline...")
    result = agent.forward(conversation, query, speakers=speakers)

    print(f"\nConstruction actions taken: {len(result.actions)}")
    for a in result.actions[:3]:
        print(f"  {a}")

    print(f"\nRetrieved facts: {len(result.retrieved_facts)}")
    for f in result.retrieved_facts:
        print(f"  {f}")

    print(f"\nFinal Answer: {result.answer}")
    print(f"Confidence: {result.confidence}")

    print("\n✅ Pipeline smoke test: PASS")
    print("\nNote: In real training, replace use_mock_llm=False and provide Qwen3-8B weights.")
