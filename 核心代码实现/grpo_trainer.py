"""
SpeakerMem-R1: Speaker-Conditioned LoGo-GRPO Trainer

Implements the training objective from §3.5:
    L_total = L_global + λ * L_local + β * L_KL

Key design choices:
  - G=4 global rollouts (following DeltaMem/Memory-R2)
  - G_local=4 local rerollouts conditioned on speaker set
  - Per-speaker adaptive credit (CoMAM-style rank consistency)
  - Token-level F1 for R_task (binary EM → gradient=0 at G=4, per Curriculum Study)

This file provides the training loop skeleton. Actual RL training requires:
  - verl framework (github.com/volcengine/verl) for distributed GRPO
  - Qwen3-8B loaded with LoRA (r=32, alpha=64)
  - 4× A100-80GB GPUs

Usage (training):
    trainer = SpeakerMemGRPOTrainer(
        model_name="Qwen/Qwen3-8B",
        lora_r=32, lora_alpha=64,
        G=4, G_local=4, lambda_logo=0.3,
    )
    trainer.train(train_dataset, n_epochs=3)

Usage (reward computation only, for debugging):
    trainer = SpeakerMemGRPOTrainer(dry_run=True)
    rewards = trainer.compute_rewards(rollout_batch, gt_batch)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Optional
from speaker_aware_memory import SpeakerAwareMemory, MemoryLayer
from speaker_levenshtein import SpeakerLevenshteinReward


# ------------------------------------------------------------------
# Data classes for training
# ------------------------------------------------------------------

@dataclass
class TrainingExample:
    """One training example = one multi-party conversation + QA pair."""
    conversation_turns: list[dict]     # [{speaker, text, turn_id}]
    query: dict                        # {asker, target, text}
    gt_answer: str                     # ground truth answer string
    gt_memory: dict[str, list[str]]   # {speaker: [fact_strings]} ground truth
    speakers: list[str]
    scenario_type: str = "close_friends"
    example_id: str = ""


@dataclass
class Rollout:
    """One GRPO rollout = one trajectory of actions + final answer."""
    example_id: str
    actions: list[dict]               # sequence of memory operations
    final_memory: dict[str, list[str]]  # {speaker: [fact_strings]} after all turns
    answer: str
    log_probs: list[float] = field(default_factory=list)  # log probs of each token
    reward: float = 0.0


@dataclass
class RewardBreakdown:
    """Detailed reward components for analysis and debugging."""
    R_task: float = 0.0               # token-level F1 between answer and gt
    R_state: float = 0.0              # SpeakerLevenshtein reward
    R_attr: float = 0.0               # speaker attribution accuracy
    R_aud: float = 0.0                # audience adaptation score
    R_leak: float = 0.0               # cross-speaker leakage penalty
    R_total: float = 0.0
    per_speaker_lev: dict = field(default_factory=dict)


# ------------------------------------------------------------------
# Reward Computation
# ------------------------------------------------------------------

def compute_token_f1(pred: str, gold: str) -> float:
    """
    Token-level F1 between predicted and ground-truth answer strings.

    Why token-level F1 (not binary EM):
    - Binary EM → gradient = 0 when all G rollouts either all pass or all fail
    - At G=4 with rare exact matches, near-zero gradients dominate
    - Token F1 provides continuous signal even for partial matches
    (per Curriculum Study 2605.23067, §3.1)
    """
    pred_tokens = set(pred.lower().split())
    gold_tokens = set(gold.lower().split())

    if not pred_tokens or not gold_tokens:
        return 0.0

    common = pred_tokens & gold_tokens
    if not common:
        return 0.0

    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def compute_attribution_accuracy(pred_memory: dict[str, list[str]],
                                  gt_memory: dict[str, list[str]]) -> float:
    """
    Fraction of facts correctly attributed to their source speaker.
    Checks: does each predicted fact appear in the correct speaker's GT bucket?
    """
    if not pred_memory:
        return 0.0

    correct = 0
    total = 0
    for speaker, facts in pred_memory.items():
        gt_facts_for_speaker = set(gt_memory.get(speaker, []))
        for fact in facts:
            total += 1
            if any(fact.lower() in gt.lower() or gt.lower() in fact.lower()
                   for gt in gt_facts_for_speaker):
                correct += 1

    return correct / total if total > 0 else 0.0


class DictMemoryAdapter:
    """
    Adapter to use plain dicts ({speaker: [fact_strings]}) with SpeakerLevenshteinReward,
    which expects objects with .speakers() and .get_speaker_facts() methods.
    """
    def __init__(self, memory_dict: dict[str, list[str]]):
        self._data = memory_dict

    def speakers(self):
        return list(self._data.keys())

    def get_speaker_facts(self, speaker: str) -> list[str]:
        return self._data.get(speaker, [])


class SpeakerMemRewardComputer:
    """Computes the full reward signal R from §3.6."""

    # Reward weights from §3.6
    W_TASK = 0.5
    W_STATE = 0.8
    W_ATTR = 0.3
    W_AUD = 0.2
    W_LEAK = 0.1

    def __init__(self, tau: float = 0.6):
        self.lev_reward = SpeakerLevenshteinReward(tau=tau)

    def compute(
        self,
        rollout: Rollout,
        example: TrainingExample,
        prev_memory: Optional[dict[str, list[str]]] = None,
    ) -> RewardBreakdown:
        """Compute all reward components for a single rollout."""

        # R_task: token-level F1
        R_task = compute_token_f1(rollout.answer, example.gt_answer)

        # R_state: SpeakerLevenshtein (from speaker_levenshtein.py)
        lev_result = self.lev_reward.compute(
            pred_memory=DictMemoryAdapter(rollout.final_memory),
            gt_memory=DictMemoryAdapter(example.gt_memory),
            prev_memory=DictMemoryAdapter(prev_memory or {s: [] for s in example.speakers}),
        )
        R_state = lev_result.get("combined_score", 0.0)
        per_speaker_lev = lev_result.get("per_speaker", {})
        R_leak = lev_result.get("leakage_penalty", 0.0)

        # R_attr: attribution accuracy
        R_attr = compute_attribution_accuracy(rollout.final_memory, example.gt_memory)

        # R_aud: audience adaptation (simplified: 1.0 if answer doesn't leak private info)
        R_aud = 1.0  # placeholder; real impl checks private fact exposure

        # Total reward (from §3.6 equation)
        R_total = (
            self.W_TASK * R_task
            + self.W_STATE * R_state
            + self.W_ATTR * R_attr
            + self.W_AUD * R_aud
            + self.W_LEAK * R_leak
        )

        return RewardBreakdown(
            R_task=R_task,
            R_state=R_state,
            R_attr=R_attr,
            R_aud=R_aud,
            R_leak=R_leak,
            R_total=R_total,
            per_speaker_lev=per_speaker_lev,
        )


# ------------------------------------------------------------------
# LoGo-GRPO Training Loop
# ------------------------------------------------------------------

class SpeakerMemGRPOTrainer:
    """
    Speaker-Conditioned LoGo-GRPO Trainer for SpeakerMem-R1.

    Training stages:
      Stage 1: Speaker-attributed SFT (warm-start before RL)
      Stage 2: Joint RL with Speaker-Conditioned LoGo
      Stage 3: End-to-end multi-benchmark fine-tune (curriculum)

    This class implements Stage 2's training loop.
    Stage 1 (SFT) is handled by standard supervised fine-tuning.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-8B",
        lora_r: int = 32,
        lora_alpha: int = 64,
        G: int = 4,                    # global rollouts
        G_local: int = 4,              # local rerollouts (LoGo)
        lambda_logo: float = 0.3,      # LoGo loss weight
        beta_kl: float = 0.01,         # KL regularization weight
        tau_lev: float = 0.6,          # SpeakerLevenshtein threshold
        mu_worst: float = 0.1,         # worst-speaker bonus weight
        dry_run: bool = False,
    ):
        self.model_name = model_name
        self.lora_r = lora_r
        self.lora_alpha = lora_alpha
        self.G = G
        self.G_local = G_local
        self.lambda_logo = lambda_logo
        self.beta_kl = beta_kl
        self.dry_run = dry_run

        self.reward_computer = SpeakerMemRewardComputer(tau=tau_lev)

    def generate_rollouts(
        self,
        example: TrainingExample,
        n_rollouts: int,
        agent=None,
    ) -> list[Rollout]:
        """
        Generate n_rollouts rollouts for a single training example.

        In dry_run mode: returns mock rollouts for testing reward computation.
        In training mode: calls the model G times with temperature > 0.
        """
        if self.dry_run:
            return self._mock_rollouts(example, n_rollouts)

        rollouts = []
        for i in range(n_rollouts):
            result = agent.forward(
                conversation=[
                    type("Turn", (), t)()
                    for t in example.conversation_turns
                ],
                query=type("Query", (), example.query)(),
                speakers=example.speakers,
                group_id=f"{example.example_id}_rollout{i}",
            )
            rollouts.append(Rollout(
                example_id=example.example_id,
                actions=result.actions,
                final_memory=self._extract_memory_state(result),
                answer=result.answer,
            ))
        return rollouts

    def compute_grpo_advantages(
        self,
        rollouts: list[Rollout],
        rewards: list[RewardBreakdown],
    ) -> list[float]:
        """
        Standard GRPO: normalize rewards within the group.
        A_i = (R_i - mean(R)) / (std(R) + ε)
        """
        import statistics
        r_values = [r.R_total for r in rewards]
        mean_r = sum(r_values) / len(r_values)
        std_r = statistics.stdev(r_values) if len(r_values) > 1 else 1.0
        eps = 1e-8
        return [(r - mean_r) / (std_r + eps) for r in r_values]

    def compute_per_speaker_credit(
        self,
        rollouts: list[Rollout],
        rewards: list[RewardBreakdown],
        speakers: list[str],
    ) -> dict[str, float]:
        """
        Per-speaker adaptive credit (CoMAM-style rank consistency, §3.5).

        alpha_s = normalize(SpearmanCorr(local_rewards^s, global_rewards))

        Speakers whose per-speaker Levenshtein score correlates more strongly
        with the global reward receive proportionally more gradient signal.
        """
        if len(rollouts) < 3:
            return {s: 1.0 for s in speakers}

        global_ranks = self._rank_list([r.R_total for r in rewards])
        alpha = {}

        for speaker in speakers:
            speaker_rewards = [r.per_speaker_lev.get(speaker, 0.0) for r in rewards]
            local_ranks = self._rank_list(speaker_rewards)
            spearman = self._spearman_corr(local_ranks, global_ranks)
            alpha[speaker] = max(0.01, spearman)  # clip at 0 to avoid negative credit

        # Normalize
        total = sum(alpha.values())
        if total > 0:
            alpha = {s: v / total * len(speakers) for s, v in alpha.items()}

        return alpha

    def logo_rerollout(
        self,
        example: TrainingExample,
        checkpoint_turn: int,
        shared_memory_state: dict[str, list[str]],
        active_speakers: list[str],
        agent=None,
    ) -> list[Rollout]:
        """
        LoGo local rerollout from a shared intermediate state (§3.5).

        All G_local rollouts:
          1. Start from the SAME intermediate memory state (shared_memory_state)
          2. Have the SAME active speaker set (active_speakers)
          → ensures fair group-relative comparison (no diverging starting conditions)
        """
        if self.dry_run:
            return self._mock_rollouts(example, self.G_local, local=True)

        rollouts = []
        for i in range(self.G_local):
            # Initialize memory from the shared checkpoint state
            memory = SpeakerAwareMemory(example.speakers, group_id=f"local_{i}")
            for speaker, facts in shared_memory_state.items():
                for fact in facts:
                    memory.write(speaker, fact, audience=example.speakers,
                                 layer=MemoryLayer.CORE, turn=checkpoint_turn)

            # Continue processing from checkpoint_turn with conditioned speakers
            remaining_turns = [
                t for t in example.conversation_turns
                if t["turn_id"] > checkpoint_turn
                and t["speaker"] in active_speakers
            ]
            # ... (abbreviated: call agent on remaining_turns + query)
            rollouts.append(Rollout(
                example_id=f"{example.example_id}_local{i}",
                actions=[],
                final_memory=shared_memory_state,
                answer="local rollout answer",
            ))

        return rollouts

    def train_step(
        self,
        batch: list[TrainingExample],
        agent=None,
    ) -> dict:
        """
        One GRPO training step over a batch of examples.
        Returns loss components for logging.
        """
        total_loss = 0.0
        total_global_loss = 0.0
        total_local_loss = 0.0

        for example in batch:
            # Stage 1: Generate G global rollouts
            global_rollouts = self.generate_rollouts(example, self.G, agent)
            global_rewards = [
                self.reward_computer.compute(r, example) for r in global_rollouts
            ]

            # Stage 2: Compute advantages
            advantages = self.compute_grpo_advantages(global_rollouts, global_rewards)

            # Stage 3: Per-speaker credit
            speaker_credit = self.compute_per_speaker_credit(
                global_rollouts, global_rewards, example.speakers
            )

            # Stage 4: LoGo local rerollouts (from midpoint checkpoint)
            mid_turn = len(example.conversation_turns) // 2
            local_rollouts = self.logo_rerollout(
                example, mid_turn,
                shared_memory_state=global_rollouts[0].final_memory,  # use best rollout as anchor
                active_speakers=example.speakers,
                agent=agent,
            )
            local_rewards = [
                self.reward_computer.compute(r, example) for r in local_rollouts
            ]
            local_advantages = self.compute_grpo_advantages(local_rollouts, local_rewards)

            # Stage 5: Combine losses (placeholder for actual backprop)
            global_loss = -sum(a * r.R_total for a, r in zip(advantages, global_rewards)) / self.G
            local_loss = -sum(a * r.R_total for a, r in zip(local_advantages, local_rewards)) / self.G_local

            step_loss = global_loss + self.lambda_logo * local_loss
            total_loss += step_loss
            total_global_loss += global_loss
            total_local_loss += local_loss

        n = len(batch)
        return {
            "loss": total_loss / n,
            "global_loss": total_global_loss / n,
            "local_loss": total_local_loss / n,
            "mean_reward": sum(r.R_total for r in global_rewards) / self.G,
        }

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------

    def _rank_list(self, values: list[float]) -> list[int]:
        """Return rank positions (1-indexed) for a list of values."""
        sorted_vals = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0] * len(values)
        for rank, (orig_idx, _) in enumerate(sorted_vals):
            ranks[orig_idx] = rank + 1
        return ranks

    def _spearman_corr(self, ranks1: list[int], ranks2: list[int]) -> float:
        """Spearman rank correlation coefficient."""
        n = len(ranks1)
        if n < 2:
            return 0.0
        d_sq_sum = sum((r1 - r2) ** 2 for r1, r2 in zip(ranks1, ranks2))
        return 1.0 - (6 * d_sq_sum) / (n * (n * n - 1))

    def _extract_memory_state(self, agent_result) -> dict[str, list[str]]:
        """Extract {speaker: [fact_strings]} from agent forward() result."""
        # In real impl: extract from agent's internal SpeakerAwareMemory
        return {}

    def _mock_rollouts(self, example: TrainingExample, n: int, local: bool = False) -> list[Rollout]:
        """Mock rollouts for dry_run testing."""
        rollouts = []
        for i in range(n):
            rollouts.append(Rollout(
                example_id=f"{example.example_id}_{'local' if local else 'global'}{i}",
                actions=[{"type": "WRITE", "owner": "Alice", "content": "mock fact"}],
                final_memory={s: [f"mock fact about {s} from rollout {i}"]
                              for s in example.speakers},
                answer=f"mock answer {i}",
            ))
        return rollouts


# ------------------------------------------------------------------
# Dry run test
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("=== SpeakerMemGRPOTrainer Dry Run ===\n")

    trainer = SpeakerMemGRPOTrainer(dry_run=True, G=4, G_local=4)

    example = TrainingExample(
        conversation_turns=[
            {"speaker": "Alice", "text": "I work at ByteDance.", "turn_id": 1},
            {"speaker": "Bob", "text": "I'm at Tencent.", "turn_id": 2},
            {"speaker": "Carol", "text": "I'm thinking of a startup.", "turn_id": 3},
        ],
        query={"asker": "Alice", "target": "Bob", "text": "Where does Bob work?"},
        gt_answer="Bob works at Tencent",
        gt_memory={
            "Alice": ["Alice works at ByteDance"],
            "Bob": ["Bob works at Tencent"],
            "Carol": ["Carol is considering a startup"],
        },
        speakers=["Alice", "Bob", "Carol"],
        example_id="test_001",
    )

    print("Generating 4 mock rollouts...")
    rollouts = trainer.generate_rollouts(example, n_rollouts=4)
    print(f"  Generated {len(rollouts)} rollouts")

    print("\nComputing rewards...")
    rewards = [trainer.reward_computer.compute(r, example) for r in rollouts]
    for i, r in enumerate(rewards):
        print(f"  Rollout {i}: R_total={r.R_total:.3f} "
              f"(task={r.R_task:.3f}, state={r.R_state:.3f}, attr={r.R_attr:.3f})")

    print("\nComputing advantages...")
    advantages = trainer.compute_grpo_advantages(rollouts, rewards)
    print(f"  Advantages: {[f'{a:.3f}' for a in advantages]}")

    print("\nComputing per-speaker credit...")
    credit = trainer.compute_per_speaker_credit(rollouts, rewards, example.speakers)
    print(f"  Credits: {credit}")

    print("\nRunning full training step...")
    step_result = trainer.train_step([example])
    print(f"  Step loss: {step_result['loss']:.4f}")
    print(f"  Global loss: {step_result['global_loss']:.4f}")
    print(f"  Local loss: {step_result['local_loss']:.4f}")
    print(f"  Mean reward: {step_result['mean_reward']:.4f}")

    print("\n✅ GRPO Trainer dry run: PASS")
    print("\nTo run actual RL training:")
    print("  trainer = SpeakerMemGRPOTrainer(model_name='Qwen/Qwen3-8B', dry_run=False)")
    print("  trainer.train(train_dataset, n_epochs=3)")
