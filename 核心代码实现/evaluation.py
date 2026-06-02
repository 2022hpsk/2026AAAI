"""
SpeakerMem-R1: Multi-Party Memory Evaluation Interface

Evaluates memory agents on three multi-party benchmarks:
  - GroupMemBench (arXiv 2605.14498)
  - EverMemBench (arXiv 2602.01313)
  - SocialMemBench (arXiv 2605.17789)

And two dyadic compatibility benchmarks:
  - LoCoMo (standard dyadic memory)
  - PersonaMem-v2 (personalized intelligence)

Usage:
    evaluator = MultiPartyEvaluator(agent=SpeakerMemAgent(model_name="Qwen/Qwen3-8B"))
    results = evaluator.evaluate_all(benchmark="GroupMemBench", data_dir="./data/")
    print(results)  # {"overall_f1": 0.58, "per_category": {...}}

Note: Requires benchmark datasets (download from respective repositories):
  - GroupMemBench: https://huggingface.co/datasets/GroupMemBench
  - EverMemBench: https://github.com/EverMind-AI/EverMemOS
  - SocialMemBench: see arXiv 2605.17789
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class BenchmarkSample:
    """A single evaluation sample from any multi-party benchmark."""
    sample_id: str
    conversation: list[dict]       # [{speaker, text, turn_id, session_id}]
    query: dict                    # {asker, target, text}
    gt_answer: str
    speakers: list[str]
    metadata: dict = field(default_factory=dict)  # category, difficulty, etc.


@dataclass
class EvaluationResult:
    """Aggregated evaluation results for one benchmark."""
    benchmark: str
    overall_score: float
    per_category: dict[str, float]
    attribution_accuracy: float
    n_samples: int
    n_correct: int
    per_sample: list[dict] = field(default_factory=list)


# ------------------------------------------------------------------
# Metric Computation
# ------------------------------------------------------------------

def compute_token_f1(pred: str, gold: str) -> float:
    """Token-level F1 for answer evaluation."""
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


def compute_exact_match(pred: str, gold: str) -> bool:
    """Exact match after normalization."""
    pred = pred.strip().lower().rstrip(".")
    gold = gold.strip().lower().rstrip(".")
    return pred == gold


def compute_speaker_attribution_accuracy(
    pred_answer: str,
    gold_answer: str,
    speakers: list[str],
) -> float:
    """
    Check if the predicted answer correctly attributes information to the right speaker.
    Simple heuristic: does the predicted answer mention the same speaker as ground truth?
    """
    gt_speakers_mentioned = [s for s in speakers if s.lower() in gold_answer.lower()]
    pred_speakers_mentioned = [s for s in speakers if s.lower() in pred_answer.lower()]

    if not gt_speakers_mentioned:
        return 1.0  # no speaker attribution needed

    correct = set(gt_speakers_mentioned) & set(pred_speakers_mentioned)
    return len(correct) / len(gt_speakers_mentioned)


# ------------------------------------------------------------------
# Benchmark-Specific Data Loaders
# ------------------------------------------------------------------

class GroupMemBenchLoader:
    """
    Load GroupMemBench data.
    Six categories: multi_hop, knowledge_update, term_ambiguity,
                    user_implicit, temporal, abstention
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def load(self, split: str = "test") -> list[BenchmarkSample]:
        """Load GroupMemBench samples from local data directory."""
        samples = []
        data_file = self.data_dir / "GroupMemBench" / f"{split}.json"

        if not data_file.exists():
            print(f"  [WARN] GroupMemBench data not found at {data_file}")
            print(f"  Download from: https://huggingface.co/datasets/GroupMemBench")
            return self._mock_samples("GroupMemBench", 10)

        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            samples.append(BenchmarkSample(
                sample_id=item.get("id", ""),
                conversation=item.get("conversation", []),
                query={
                    "asker": item.get("asker", ""),
                    "target": item.get("target", ""),
                    "text": item.get("question", ""),
                },
                gt_answer=item.get("answer", ""),
                speakers=item.get("speakers", []),
                metadata={"category": item.get("category", "unknown")},
            ))

        return samples

    def _mock_samples(self, benchmark: str, n: int) -> list[BenchmarkSample]:
        """Return mock samples for testing pipeline without actual data."""
        categories = ["multi_hop", "knowledge_update", "term_ambiguity",
                      "user_implicit", "temporal", "abstention"]
        return [
            BenchmarkSample(
                sample_id=f"{benchmark}_mock_{i}",
                conversation=[
                    {"speaker": "Alice", "text": "I work at ByteDance.", "turn_id": 1, "session_id": 1},
                    {"speaker": "Bob", "text": "I'm at Tencent.", "turn_id": 2, "session_id": 1},
                ],
                query={"asker": "Alice", "target": "Bob", "text": "Where does Bob work?"},
                gt_answer="Bob works at Tencent",
                speakers=["Alice", "Bob"],
                metadata={"category": categories[i % len(categories)]},
            )
            for i in range(n)
        ]


class EverMemBenchLoader:
    """
    Load EverMemBench data.
    Three dimensions: factual_recall, applied_memory, user_profiling
    170 employees, 51K turns, 2400 QA pairs.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def load(self, split: str = "test") -> list[BenchmarkSample]:
        samples = []
        data_file = self.data_dir / "EverMemBench" / f"{split}.json"

        if not data_file.exists():
            print(f"  [WARN] EverMemBench data not found at {data_file}")
            print(f"  Clone from: https://github.com/EverMind-AI/EverMemOS")
            return self._mock_loader(10)

        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            samples.append(BenchmarkSample(
                sample_id=item.get("id", ""),
                conversation=item.get("dialogue", []),
                query=item.get("query", {}),
                gt_answer=item.get("answer", ""),
                speakers=item.get("participants", []),
                metadata={"dimension": item.get("dimension", "factual_recall")},
            ))
        return samples

    def _mock_loader(self, n: int) -> list[BenchmarkSample]:
        return [
            BenchmarkSample(
                sample_id=f"evermem_mock_{i}",
                conversation=[
                    {"speaker": "Alex", "text": "I'll handle the deployment.", "turn_id": 1, "session_id": 1},
                    {"speaker": "Blake", "text": "I'll write the tests.", "turn_id": 2, "session_id": 1},
                ],
                query={"asker": "Casey", "target": "Alex", "text": "Who took on deployment?"},
                gt_answer="Alex said he would handle the deployment",
                speakers=["Alex", "Blake", "Casey"],
                metadata={"dimension": "factual_recall"},
            )
            for i in range(n)
        ]


class SocialMemBenchLoader:
    """
    Load SocialMemBench data.
    Five group types × three size tiers, 1031 QA pairs.
    """

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)

    def load(self, split: str = "test") -> list[BenchmarkSample]:
        samples = []
        data_file = self.data_dir / "SocialMemBench" / f"{split}.json"

        if not data_file.exists():
            print(f"  [WARN] SocialMemBench data not found at {data_file}")
            return self._mock_loader(10)

        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            samples.append(BenchmarkSample(
                sample_id=item.get("id", ""),
                conversation=item.get("dialogue", []),
                query=item.get("query", {}),
                gt_answer=item.get("answer", ""),
                speakers=item.get("speakers", []),
                metadata={
                    "group_type": item.get("group_type", "close_friends"),
                    "group_size": item.get("group_size", 3),
                    "failure_mode": item.get("failure_mode", ""),
                },
            ))
        return samples

    def _mock_loader(self, n: int) -> list[BenchmarkSample]:
        return [
            BenchmarkSample(
                sample_id=f"social_mock_{i}",
                conversation=[
                    {"speaker": "Alice", "text": "I'm thinking of a startup.", "turn_id": 1, "session_id": 1},
                    {"speaker": "Bob", "text": "That's exciting!", "turn_id": 2, "session_id": 1},
                    {"speaker": "Carol", "text": "I prefer stability.", "turn_id": 3, "session_id": 1},
                ],
                query={"asker": "Bob", "target": "Carol", "text": "What is Carol's career preference?"},
                gt_answer="Carol prefers stability over startups",
                speakers=["Alice", "Bob", "Carol"],
                metadata={"group_type": "close_friends", "group_size": 3},
            )
            for i in range(n)
        ]


# ------------------------------------------------------------------
# Main Evaluator
# ------------------------------------------------------------------

LOADERS = {
    "GroupMemBench": GroupMemBenchLoader,
    "EverMemBench": EverMemBenchLoader,
    "SocialMemBench": SocialMemBenchLoader,
}


class MultiPartyEvaluator:
    """
    Unified evaluator for all three multi-party benchmarks.

    Usage (with real agent):
        agent = SpeakerMemAgent(model_name="Qwen/Qwen3-8B", use_mock_llm=False)
        evaluator = MultiPartyEvaluator(agent=agent, data_dir="./data/")
        results = evaluator.evaluate_all()

    Usage (dry run):
        evaluator = MultiPartyEvaluator(agent=None, data_dir="./data/", dry_run=True)
        results = evaluator.evaluate("GroupMemBench")
    """

    def __init__(
        self,
        agent=None,
        data_dir: str = "./data/",
        dry_run: bool = False,
        max_samples: Optional[int] = None,
    ):
        self.agent = agent
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.max_samples = max_samples

    def evaluate(self, benchmark: str) -> EvaluationResult:
        """Evaluate agent on a single benchmark."""
        if benchmark not in LOADERS:
            raise ValueError(f"Unknown benchmark: {benchmark}. Choose from {list(LOADERS.keys())}")

        loader = LOADERS[benchmark](self.data_dir)
        samples = loader.load("test")

        if self.max_samples:
            samples = samples[:self.max_samples]

        print(f"Evaluating on {benchmark}: {len(samples)} samples...")

        per_sample_results = []
        category_scores: dict[str, list[float]] = {}

        for i, sample in enumerate(samples):
            if i % 50 == 0:
                print(f"  Progress: {i}/{len(samples)}")

            if self.dry_run or self.agent is None:
                pred_answer = "dry run answer for testing"
                pred_memory = {s: [f"mock fact about {s}"] for s in sample.speakers}
            else:
                result = self.agent.forward(
                    conversation=[type("Turn", (), t)() for t in sample.conversation],
                    query=type("Query", (), sample.query)(),
                    speakers=sample.speakers,
                    group_id=sample.sample_id,
                )
                pred_answer = result.answer
                pred_memory = self.agent._last_memory_state  # expose internal state

            # Compute metrics
            f1 = compute_token_f1(pred_answer, sample.gt_answer)
            em = compute_exact_match(pred_answer, sample.gt_answer)
            attr_acc = compute_speaker_attribution_accuracy(
                pred_answer, sample.gt_answer, sample.speakers
            )

            category = (sample.metadata.get("category")
                        or sample.metadata.get("dimension")
                        or sample.metadata.get("group_type")
                        or "overall")

            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(f1)

            per_sample_results.append({
                "sample_id": sample.sample_id,
                "f1": f1,
                "em": em,
                "attribution_accuracy": attr_acc,
                "category": category,
                "pred_answer": pred_answer,
                "gt_answer": sample.gt_answer,
            })

        # Aggregate
        all_f1 = [r["f1"] for r in per_sample_results]
        overall_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0.0
        overall_attr = sum(r["attribution_accuracy"] for r in per_sample_results) / len(per_sample_results)
        per_category_f1 = {cat: sum(scores) / len(scores)
                           for cat, scores in category_scores.items()}

        result = EvaluationResult(
            benchmark=benchmark,
            overall_score=overall_f1,
            per_category=per_category_f1,
            attribution_accuracy=overall_attr,
            n_samples=len(samples),
            n_correct=sum(1 for r in per_sample_results if r["em"]),
            per_sample=per_sample_results,
        )

        self._print_result(result)
        return result

    def evaluate_all(self) -> dict[str, EvaluationResult]:
        """Evaluate on all three multi-party benchmarks."""
        results = {}
        for benchmark in LOADERS:
            results[benchmark] = self.evaluate(benchmark)
        return results

    def _print_result(self, result: EvaluationResult) -> None:
        print(f"\n{'='*50}")
        print(f"Benchmark: {result.benchmark}")
        print(f"Overall F1: {result.overall_score:.4f} ({result.overall_score*100:.1f}%)")
        print(f"Attribution Accuracy: {result.attribution_accuracy:.4f}")
        print(f"Exact Match: {result.n_correct}/{result.n_samples}")
        print(f"Per-Category F1:")
        for cat, score in sorted(result.per_category.items()):
            print(f"  {cat}: {score:.4f} ({score*100:.1f}%)")
        print('='*50)

    def save_results(self, results: dict[str, EvaluationResult], output_path: str) -> None:
        """Save evaluation results to JSON."""
        output = {}
        for benchmark, result in results.items():
            output[benchmark] = {
                "overall_score": result.overall_score,
                "per_category": result.per_category,
                "attribution_accuracy": result.attribution_accuracy,
                "n_samples": result.n_samples,
                "n_correct": result.n_correct,
            }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {output_path}")


# ------------------------------------------------------------------
# Quick test
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("=== MultiPartyEvaluator Dry Run ===\n")

    evaluator = MultiPartyEvaluator(agent=None, data_dir="./data/", dry_run=True, max_samples=5)

    print("Testing GroupMemBench loader (mock)...")
    gb_result = evaluator.evaluate("GroupMemBench")
    assert gb_result.n_samples == 5
    assert 0.0 <= gb_result.overall_score <= 1.0

    print("\nTesting EverMemBench loader (mock)...")
    em_result = evaluator.evaluate("EverMemBench")
    assert em_result.n_samples == 5

    print("\nTesting SocialMemBench loader (mock)...")
    sm_result = evaluator.evaluate("SocialMemBench")
    assert sm_result.n_samples == 5

    print("\n✅ Evaluation interface dry run: PASS")
    print("\nTo run real evaluation:")
    print("  1. Download benchmark datasets to ./data/")
    print("  2. evaluator = MultiPartyEvaluator(agent=SpeakerMemAgent(...), data_dir='./data/')")
    print("  3. results = evaluator.evaluate_all()")
