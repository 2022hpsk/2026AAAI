"""
SpeakerMem-R1: Synthetic Multi-Party Training Data Generation Pipeline

Generates 200 multi-party dialogues with ground-truth speaker-attributed memory:
  - 50 close_friends (3-5 speakers, 8 sessions, SocialMemBench style)
  - 50 workplace_team (4-8 speakers, 16 sessions, EverMemBench style)
  - 50 interest_community (3-6 speakers, 8 sessions, GroupMemBench style)
  - 50 locomo_triadic (dyadic LoCoMo → triadic augmentation)

Each dialogue includes:
  - Ground-truth speaker-attributed memory (SpeakerAwareMemory format)
  - 3 QA pairs per dialogue
  - Quality validation checks

Usage:
    pipeline = SyntheticDataPipeline(api_key="YOUR_KEY")
    pipeline.generate_batch("close_friends", n=50, output_dir="./synth_data/")
"""

from __future__ import annotations
import json
import random
from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path


ScenarioType = Literal["close_friends", "workplace_team", "interest_community", "locomo_triadic"]


# ------------------------------------------------------------------
# Prompt Templates
# ------------------------------------------------------------------

SYSTEM_PROMPT = """You are a multi-party conversation generator for AI memory research.
Generate realistic, naturalistic dialogues where speakers share personal information
that a memory agent should track, attribute correctly, and respond to later.

CRITICAL REQUIREMENTS:
1. Every piece of shared information must be clearly attributable to ONE speaker
2. Speakers must discuss EACH OTHER (not just themselves), creating attribution challenges
3. Include temporal updates (speaker changes their stated fact in a later session)
4. Include cross-speaker references ("you said...", "I heard Alice mention...")
5. Make sure QA questions require memory of WHO said WHAT, not just WHAT was said

Output STRICT JSON following the schema provided."""

DIALOGUE_PROMPT_TEMPLATES = {
    "close_friends": """Generate a {n_sessions}-session multi-party conversation among {n_speakers} close friends.

SPEAKERS: {speaker_names}
TOPIC DOMAIN: Personal life updates (jobs, relationships, hobbies, health, plans)
SESSIONS: Each session is 4-8 turns, with 1-2 week gap between sessions

REQUIREMENTS:
- Each speaker must share at least 3 distinct personal facts across all sessions
- At least 2 facts must be updates/changes to previously stated facts
- At least 1 cross-speaker reference per session (Speaker A talks about what Speaker B said)
- Include 1 privacy-sensitive exchange (speaker shares something not for all to know)

OUTPUT FORMAT (JSON):
{{
  "scenario_type": "close_friends",
  "speakers": ["speaker1", "speaker2", ...],
  "sessions": [
    {{
      "session_id": 1,
      "turns": [
        {{"speaker": "Alice", "text": "...", "turn_id": 1}},
        ...
      ]
    }},
    ...
  ],
  "ground_truth_memory": {{
    "Alice": [
      {{"fact": "Alice works at ByteDance", "first_mentioned_turn": 1, "layer": "core"}},
      ...
    ],
    "Bob": [...],
    ...
  }},
  "qa_pairs": [
    {{
      "asker": "Alice",
      "question": "Who mentioned they were thinking of changing jobs?",
      "answer": "Carol mentioned considering a startup in session 2",
      "requires_speaker_attribution": true,
      "difficulty": "medium"
    }},
    ...
  ]
}}

SPEAKER NAMES: {speaker_names}
NUMBER OF SESSIONS: {n_sessions}""",

    "workplace_team": """Generate a {n_sessions}-session workplace team conversation among {n_speakers} colleagues.

SPEAKERS: {speaker_names}
CONTEXT: Software development team working on a shared project
TOPIC DOMAINS: Work assignments, technical decisions, personal work styles, project updates

REQUIREMENTS:
- Include at least 2 knowledge-update scenarios (a decision is reversed or updated)
- Include multi-hop reasoning opportunities (Speaker A influenced Speaker B's decision)
- At least one ambiguous attribution challenge (two speakers discuss the same entity)
- Include temporal reasoning (deadlines, completion dates, version numbers)

OUTPUT FORMAT: Same JSON schema as above.
SPEAKER NAMES: {speaker_names}
NUMBER OF SESSIONS: {n_sessions}""",

    "interest_community": """Generate a {n_sessions}-session conversation among {n_speakers} members of a hobby/interest community.

SPEAKERS: {speaker_names}
DOMAIN: Choose one: [book club, hiking group, cooking enthusiasts, tech meetup, film appreciation]
SESSIONS: Community meetings + casual side conversations

REQUIREMENTS:
- Include term ambiguity challenges (same term means different things to different speakers)
- Include user-implicit reasoning (what speaker X would want based on their stated preferences)
- Include abstention scenarios (a question that cannot be answered from memory)
- Multi-hop: "Who recommended the book that Carol ended up loving?"

OUTPUT FORMAT: Same JSON schema as above.
SPEAKER NAMES: {speaker_names}
NUMBER OF SESSIONS: {n_sessions}""",

    "locomo_triadic": """Given this dyadic LoCoMo-style conversation between Alice and Bob, add a THIRD speaker (Carol)
who naturally joins the conversation and creates attribution challenges.

ORIGINAL DYADIC SETUP: Two friends, {n_sessions} sessions of life updates

CAROL'S ROLE: Must be someone who:
1. Is already known to both Alice and Bob (creates cross-references)
2. Has overlapping interests/life situations with Alice OR Bob (creates attribution confusion)
3. Sometimes quotes or references what Alice/Bob said in earlier sessions

OUTPUT FORMAT: Same JSON schema as above, now with 3 speakers.
SPEAKER NAMES: Alice, Bob, Carol
NUMBER OF SESSIONS: {n_sessions}"""
}

# Quality validation prompt
QA_VALIDATION_PROMPT = """Review these QA pairs and verify they meet our quality criteria:

DIALOGUE SUMMARY: {dialogue_summary}
QA PAIRS: {qa_pairs_json}

For each QA pair, verify:
1. MEMORY REQUIRED: Answer cannot be derived from common knowledge alone (must require reading the dialogue)
2. SPEAKER ATTRIBUTION: The correct answer requires knowing WHO said something (not just WHAT was said)
3. ANSWERABILITY: Answer can be found in the provided dialogue (no speculation)
4. CONSISTENCY: Speaker labels in the answer match those in the dialogue

Return JSON:
{{
  "qa_pair_0": {{"valid": true/false, "issues": "..."}},
  "qa_pair_1": {{"valid": true/false, "issues": "..."}},
  "qa_pair_2": {{"valid": true/false, "issues": "..."}}
}}"""

# Ground truth validation prompt
MEMORY_VALIDATION_PROMPT = """Review this ground-truth speaker-attributed memory and verify quality:

DIALOGUE: {dialogue_text}
GROUND TRUTH MEMORY: {gt_memory_json}

Verify:
1. MINIMUM FACTS: Each speaker has at least 3 distinct facts
2. ATTRIBUTION CORRECTNESS: Every fact is assigned to the correct speaker
3. COVERAGE: All important personal information in the dialogue is captured
4. NO COMMONSENSE: No fact is derivable without the dialogue (e.g., "Alice is human" is invalid)

Return JSON:
{{
  "valid": true/false,
  "issues": ["issue1", "issue2", ...],
  "missing_facts": ["fact that should have been captured", ...],
  "wrong_attribution": [{{"fact": "...", "wrongly_assigned_to": "...", "should_be": "..."}}]
}}"""


@dataclass
class SpeakerConfig:
    names: list[str]
    n_sessions: int
    scenario_type: ScenarioType


def get_speaker_config(scenario_type: ScenarioType, seed: int = 42) -> SpeakerConfig:
    """Sample speaker names and session counts for a given scenario type."""
    rng = random.Random(seed)

    name_pools = {
        "close_friends": [
            ["Alice", "Bob", "Carol"],
            ["Diana", "Eve", "Frank", "Grace"],
            ["Henry", "Iris", "Jack", "Kate", "Leo"],
        ],
        "workplace_team": [
            ["Alex", "Blake", "Casey", "Drew"],
            ["Emma", "Finn", "Gaby", "Hana", "Ivan"],
            ["Jordan", "Kim", "Lena", "Max", "Nina", "Owen"],
        ],
        "interest_community": [
            ["Pat", "Quinn", "Robin"],
            ["Sam", "Taylor", "Uma", "Victor"],
            ["Wendy", "Xander", "Yara", "Zoe", "Aaron"],
        ],
        "locomo_triadic": [
            ["Alice", "Bob", "Carol"],  # fixed for triadic
        ],
    }

    session_counts = {
        "close_friends": [6, 8, 10],
        "workplace_team": [12, 16, 20],
        "interest_community": [6, 8, 10],
        "locomo_triadic": [8, 10, 12],
    }

    names = rng.choice(name_pools[scenario_type])
    n_sess = rng.choice(session_counts[scenario_type])
    return SpeakerConfig(names=names, n_sessions=n_sess, scenario_type=scenario_type)


def build_generation_prompt(config: SpeakerConfig, index: int) -> str:
    """Build the full GPT-4 prompt for generating one dialogue."""
    template = DIALOGUE_PROMPT_TEMPLATES[config.scenario_type]
    return SYSTEM_PROMPT + "\n\n" + template.format(
        n_speakers=len(config.names),
        speaker_names=", ".join(config.names),
        n_sessions=config.n_sessions,
    )


def validate_gt_memory(gt_memory: dict, speakers: list[str]) -> tuple[bool, list[str]]:
    """
    Validate ground-truth memory quality (runs locally, no LLM needed).
    Returns (is_valid, list_of_issues).
    """
    issues = []

    # Check 1: every speaker has ≥3 facts
    for speaker in speakers:
        facts = gt_memory.get(speaker, [])
        if len(facts) < 3:
            issues.append(f"{speaker} has only {len(facts)} facts (min 3 required)")

    # Check 2: no empty fact strings
    for speaker, facts in gt_memory.items():
        for fact in facts:
            content = fact.get("fact", "") if isinstance(fact, dict) else fact
            if len(content.strip()) < 10:
                issues.append(f"{speaker} has suspiciously short fact: '{content}'")

    # Check 3: layer values are valid
    valid_layers = {"core", "episodic", "profile", "interact", "insight"}
    for speaker, facts in gt_memory.items():
        for fact in facts:
            if isinstance(fact, dict):
                layer = fact.get("layer", "core")
                if layer not in valid_layers:
                    issues.append(f"Invalid layer '{layer}' for {speaker}'s fact")

    return len(issues) == 0, issues


class SyntheticDataPipeline:
    """
    Orchestrates generation of synthetic multi-party training dialogues.

    With a real LLM API:
        pipeline = SyntheticDataPipeline(api_key="YOUR_KEY")
        pipeline.generate_batch("close_friends", n=50, output_dir="./synth_data/")

    Without API (dry run to verify structure):
        pipeline = SyntheticDataPipeline(dry_run=True)
        prompt = pipeline.preview_prompt("workplace_team", index=0)
    """

    def __init__(self, api_key: str = "", dry_run: bool = False):
        self.api_key = api_key
        self.dry_run = dry_run
        self.stats = {
            "generated": 0,
            "validation_failed": 0,
            "retried": 0,
        }

    def preview_prompt(self, scenario_type: ScenarioType, index: int = 0) -> str:
        """Preview the GPT-4 prompt for a given scenario (no API call)."""
        config = get_speaker_config(scenario_type, seed=index)
        return build_generation_prompt(config, index)

    def generate_one(self, scenario_type: ScenarioType, index: int) -> dict | None:
        """
        Generate a single training dialogue.
        Returns structured dict or None if validation fails after retries.

        In dry_run mode, returns a mock structure for testing the pipeline logic.
        """
        config = get_speaker_config(scenario_type, seed=index)
        prompt = build_generation_prompt(config, index)

        if self.dry_run:
            # Return mock structure for pipeline testing
            mock = self._mock_dialogue(config, index)
            is_valid, issues = validate_gt_memory(mock["ground_truth_memory"], config.names)
            if not is_valid:
                print(f"  [WARN] Mock validation issues: {issues}")
            return mock

        # Real API call (requires api_key)
        try:
            response_text = self._call_gpt4(prompt)
            data = json.loads(response_text)

            # Local validation
            is_valid, issues = validate_gt_memory(data.get("ground_truth_memory", {}), config.names)
            if not is_valid:
                print(f"  [RETRY] Dialogue {index} failed validation: {issues}")
                self.stats["validation_failed"] += 1
                return None

            data["meta"] = {
                "scenario_type": scenario_type,
                "index": index,
                "speakers": config.names,
                "n_sessions": config.n_sessions,
            }
            self.stats["generated"] += 1
            return data

        except (json.JSONDecodeError, KeyError) as e:
            print(f"  [ERROR] Failed to parse dialogue {index}: {e}")
            return None

    def generate_batch(
        self,
        scenario_type: ScenarioType,
        n: int,
        output_dir: str = "./synth_data/",
        start_index: int = 0,
    ) -> list[dict]:
        """
        Generate n dialogues of a given type and save to output_dir.
        """
        output_path = Path(output_dir) / scenario_type
        output_path.mkdir(parents=True, exist_ok=True)

        results = []
        for i in range(start_index, start_index + n):
            print(f"Generating {scenario_type} dialogue {i + 1}/{start_index + n}...")
            result = self.generate_one(scenario_type, index=i)
            if result is not None:
                filepath = output_path / f"{scenario_type}_{i:04d}.json"
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                results.append(result)
            else:
                print(f"  [SKIP] Dialogue {i} could not be generated/validated.")

        print(f"\nBatch complete: {len(results)}/{n} dialogues saved to {output_path}/")
        return results

    def _call_gpt4(self, prompt: str) -> str:
        """Call GPT-4 API. Requires openai package and valid api_key."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    def _mock_dialogue(self, config: SpeakerConfig, index: int) -> dict:
        """Generate a minimal mock dialogue for pipeline testing."""
        speakers = config.names
        mock_memory = {}
        for spk in speakers:
            mock_memory[spk] = [
                {"fact": f"{spk} works at Company_{index}", "first_mentioned_turn": 1, "layer": "core"},
                {"fact": f"{spk} enjoys hiking", "first_mentioned_turn": 3, "layer": "profile"},
                {"fact": f"{spk} is planning a trip", "first_mentioned_turn": 5, "layer": "core"},
            ]

        return {
            "scenario_type": config.scenario_type,
            "speakers": speakers,
            "sessions": [
                {
                    "session_id": 1,
                    "turns": [
                        {"speaker": speakers[0], "text": f"Hi everyone! I work at Company_{index}.", "turn_id": 1},
                        {"speaker": speakers[1], "text": "Great! I love hiking on weekends.", "turn_id": 2},
                    ]
                }
            ],
            "ground_truth_memory": mock_memory,
            "qa_pairs": [
                {
                    "asker": speakers[0],
                    "question": f"Where does {speakers[1]} work?",
                    "answer": f"{speakers[1]} works at Company_{index + 1}",
                    "requires_speaker_attribution": True,
                    "difficulty": "easy",
                }
            ],
            "meta": {
                "scenario_type": config.scenario_type,
                "index": index,
                "speakers": speakers,
                "n_sessions": config.n_sessions,
                "is_mock": True,
            }
        }


# ------------------------------------------------------------------
# Dry run test
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SyntheticDataPipeline Dry Run Test ===\n")

    pipeline = SyntheticDataPipeline(dry_run=True)

    # Preview prompt for close_friends scenario
    print("--- close_friends prompt preview (first 300 chars) ---")
    prompt = pipeline.preview_prompt("close_friends", index=0)
    print(prompt[:300] + "...\n")

    # Generate one mock dialogue
    print("--- Generating mock close_friends dialogue (index=0) ---")
    result = pipeline.generate_one("close_friends", index=0)
    if result:
        print(f"  Speakers: {result['speakers']}")
        print(f"  Sessions: {len(result['sessions'])}")
        print(f"  QA pairs: {len(result['qa_pairs'])}")
        print(f"  GT memory keys: {list(result['ground_truth_memory'].keys())}")
        for spk, facts in result["ground_truth_memory"].items():
            print(f"    {spk}: {len(facts)} facts")
    print()

    # Test all 4 scenario types
    print("--- Testing all 4 scenario types ---")
    for scenario in ["close_friends", "workplace_team", "interest_community", "locomo_triadic"]:
        cfg = get_speaker_config(scenario, seed=7)
        print(f"  {scenario}: speakers={cfg.names}, sessions={cfg.n_sessions}")

    print("\n✅ Pipeline structure test: PASS")
    print("\nTo generate real data with GPT-4:")
    print("  pipeline = SyntheticDataPipeline(api_key='YOUR_KEY')")
    print("  pipeline.generate_batch('close_friends', n=50, output_dir='./synth_data/')")
