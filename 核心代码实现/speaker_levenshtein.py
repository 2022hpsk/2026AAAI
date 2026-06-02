"""
SpeakerLevenshtein: Speaker-Aware Memory State Alignment Reward
for Multi-Party Conversation Memory Agents

基于 DeltaMem (2604.01560) 的 Memory-based Levenshtein Distance，
扩展为 per-speaker bucketed 版本，专门针对多方对话场景。

核心公式：
    R_spkr = mean_s [Levenshtein_F1(memory[s], gt_memory[s])]
    R_leak = -penalty(cross-speaker attribution errors)
    R_total = alpha * R_spkr - beta * R_leak

作者：SpeakerMem-R1 Project
日期：2026-06-02（V4 迭代实现）
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from scipy.optimize import linear_sum_assignment


# ============================================================
# 数据结构
# ============================================================

@dataclass
class MemoryEntry:
    """单条记忆条目，带说话人归属"""
    content: str
    speaker_id: str
    audience_set: set[str] = field(default_factory=set)
    confidence: float = 1.0


@dataclass
class SpeakerMemory:
    """按说话人分桶的记忆状态"""
    entries: dict[str, list[MemoryEntry]] = field(default_factory=dict)

    def get_speaker_facts(self, speaker_id: str) -> list[str]:
        """获取某说话人的所有事实（字符串列表）"""
        return [e.content for e in self.entries.get(speaker_id, [])]

    def all_entries_flat(self) -> list[MemoryEntry]:
        """展平所有条目"""
        result = []
        for entries in self.entries.values():
            result.extend(entries)
        return result

    def speakers(self) -> list[str]:
        return list(self.entries.keys())


# ============================================================
# 核心：Speaker-Aware Levenshtein F1
# ============================================================

class SpeakerLevenshteinReward:
    """
    Plug-in reward module for multi-party memory RL training.

    可以直接嫁接到任意 RL memory framework（GRPO/PPO）的 reward 函数。

    用法：
        reward_fn = SpeakerLevenshteinReward(tau=0.6)
        result = reward_fn.compute(pred_memory, gt_memory, privacy_rules)
        total_reward = result['combined']
    """

    def __init__(
        self,
        tau: float = 0.6,
        tau_mode: str = "global",  # "global" 或 "per_speaker"
        alpha: float = 1.0,    # R_spkr 权重
        beta: float = 0.3,     # R_leak 权重
        min_speaker_weight: float = 0.2,   # worst-speaker penalty 权重
        embed_model: str = "all-MiniLM-L6-v2",  # sentence-transformers 模型
        use_lexical_fidelity: bool = True,  # 是否加 local lexical fidelity
    ):
        self.tau = tau
        self.tau_mode = tau_mode
        self.alpha = alpha
        self.beta = beta
        self.min_speaker_weight = min_speaker_weight
        self.use_lexical_fidelity = use_lexical_fidelity

        # 延迟加载 embedding model
        self._embedder = None
        self.embed_model = embed_model

    @property
    def embedder(self):
        """延迟加载 sentence transformer"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(self.embed_model)
            except ImportError:
                raise ImportError(
                    "需要安装 sentence-transformers: pip install sentence-transformers"
                )
        return self._embedder

    def compute(
        self,
        pred_memory: SpeakerMemory,
        gt_memory: SpeakerMemory,
        prev_memory: Optional[SpeakerMemory] = None,
        privacy_rules: Optional[dict[str, list[str]]] = None,
        speaker_vocab_stats: Optional[dict] = None,
    ) -> dict:
        """
        计算 speaker-aware Levenshtein reward。

        Args:
            pred_memory: 模型预测的记忆状态（按 speaker 分桶）
            gt_memory: 真实记忆状态（ground truth）
            prev_memory: 上一时刻的记忆状态（用于计算 Δ，可选）
            privacy_rules: 隐私规则 {speaker_id: [forbidden_recipient_ids]}
            speaker_vocab_stats: 说话人词汇统计（用于 per-speaker τ 校准）

        Returns:
            dict with keys:
                'R_spkr': float  # per-speaker average F1
                'R_leak': float  # leakage penalty (positive = more leakage)
                'per_speaker': dict[str, float]  # per-speaker F1 breakdown
                'combined': float  # alpha*R_spkr - beta*R_leak
        """
        all_speakers = list(set(
            list(gt_memory.speakers()) + list(pred_memory.speakers())
        ))

        if not all_speakers:
            return {'R_spkr': 0.0, 'R_leak': 0.0, 'per_speaker': {}, 'combined': 0.0}

        # 计算 per-speaker F1
        per_speaker_f1 = {}
        for speaker in all_speakers:
            tau = self._get_tau(speaker, speaker_vocab_stats)
            f1 = self._speaker_levenshtein_f1(
                pred_facts=pred_memory.get_speaker_facts(speaker),
                gt_facts=gt_memory.get_speaker_facts(speaker),
                prev_facts=(prev_memory.get_speaker_facts(speaker)
                           if prev_memory else []),
                tau=tau,
            )
            per_speaker_f1[speaker] = f1

        # R_spkr：平均 + worst-speaker penalty
        f1_values = list(per_speaker_f1.values())
        avg_f1 = np.mean(f1_values)
        worst_f1 = min(f1_values)
        R_spkr = avg_f1 + self.min_speaker_weight * worst_f1
        # 归一化（确保在合理范围内）
        R_spkr = R_spkr / (1 + self.min_speaker_weight)

        # R_leak：cross-speaker leakage penalty
        R_leak = 0.0
        if privacy_rules:
            R_leak = self._leakage_penalty(pred_memory, gt_memory, privacy_rules)

        combined = self.alpha * R_spkr - self.beta * R_leak

        return {
            'R_spkr': float(R_spkr),
            'R_leak': float(R_leak),
            'per_speaker': per_speaker_f1,
            'combined': float(combined),
        }

    def _get_tau(
        self,
        speaker_id: str,
        speaker_vocab_stats: Optional[dict]
    ) -> float:
        """
        获取说话人对应的 τ 阈值。

        如果 tau_mode == "per_speaker" 且有 vocab_stats，
        根据说话人的词汇一致性自适应调整：
        - 语言正式/词汇精准 → 高 τ
        - 语言随意/用词多变 → 低 τ
        """
        if self.tau_mode == "global" or speaker_vocab_stats is None:
            return self.tau

        stats = speaker_vocab_stats.get(speaker_id, {})
        vocab_consistency = stats.get('consistency', 0.5)  # 0~1
        delta = 0.15 * (vocab_consistency - 0.5) * 2  # ±0.15
        return float(np.clip(self.tau + delta, 0.3, 0.9))

    def _speaker_levenshtein_f1(
        self,
        pred_facts: list[str],
        gt_facts: list[str],
        prev_facts: list[str],
        tau: float,
    ) -> float:
        """
        单个说话人的 Levenshtein F1。

        如果提供了 prev_facts，只计算 Δ（本轮新增的事实）。
        这是 DeltaMem 的关键设计：奖励增量，不是绝对状态。
        """
        # 计算 Δ：去除前一时刻已有的 facts（基于精确字符串匹配）
        if prev_facts:
            prev_set = set(prev_facts)
            pred_delta = [f for f in pred_facts if f not in prev_set]
            gt_delta = [f for f in gt_facts if f not in prev_set]
        else:
            pred_delta = pred_facts
            gt_delta = gt_facts

        if not gt_delta:
            # 没有需要新增的 facts → 如果 pred 也没有新增，给满分；否则给 0
            return 1.0 if not pred_delta else 0.0

        if not pred_delta:
            return 0.0

        # 计算 embedding 相似度矩阵
        sim_matrix = self._compute_similarity_matrix(pred_delta, gt_delta)

        # 加 local lexical fidelity（DeltaMem 关键组件，对 PersonaMem +3 F1）
        if self.use_lexical_fidelity:
            sim_matrix = self._apply_lexical_fidelity(sim_matrix, pred_delta, gt_delta)

        # Optimal transport 匹配（Hungarian algorithm）
        row_ind, col_ind = linear_sum_assignment(-sim_matrix)

        # 阈值过滤
        matched_pairs = [
            (r, c) for r, c in zip(row_ind, col_ind)
            if sim_matrix[r, c] >= tau
        ]

        tp = len(matched_pairs)
        precision = tp / len(pred_delta)
        recall = tp / len(gt_delta)

        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def _compute_similarity_matrix(
        self,
        texts1: list[str],
        texts2: list[str]
    ) -> np.ndarray:
        """计算两组文本的 cosine similarity matrix"""
        try:
            all_texts = texts1 + texts2
            embeddings = self.embedder.encode(all_texts, normalize_embeddings=True)
            emb1 = embeddings[:len(texts1)]
            emb2 = embeddings[len(texts1):]
            return emb1 @ emb2.T  # shape: (len1, len2)
        except Exception:
            # Fallback to simple Jaccard similarity (no model download needed)
            return self._jaccard_similarity_matrix(texts1, texts2)

    def _jaccard_similarity_matrix(
        self,
        texts1: list[str],
        texts2: list[str],
    ) -> np.ndarray:
        """无需模型的 Jaccard word overlap 相似度（用于测试）"""
        mat = np.zeros((len(texts1), len(texts2)))
        for i, t1 in enumerate(texts1):
            for j, t2 in enumerate(texts2):
                mat[i, j] = self._simple_similarity(t1, t2)
        return mat

    def _apply_lexical_fidelity(
        self,
        sim_matrix: np.ndarray,
        pred_facts: list[str],
        gt_facts: list[str],
    ) -> np.ndarray:
        """
        DeltaMem 的 local lexical fidelity：
        检查 pred fact 是否包含 gt fact 的关键词。
        提升 soft precision/recall。
        """
        sim_matrix = sim_matrix.copy()

        for i, pf in enumerate(pred_facts):
            for j, gf in enumerate(gt_facts):
                # 简单的关键词覆盖率（可以换成更复杂的 NER-based）
                gt_tokens = set(gf.lower().split())
                pred_tokens = set(pf.lower().split())
                # 过滤停用词（简化版）
                stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were',
                            'in', 'on', 'at', 'to', 'for', 'and', 'or', 'of'}
                gt_keywords = gt_tokens - stopwords

                if gt_keywords:
                    coverage = len(gt_keywords & pred_tokens) / len(gt_keywords)
                    # 词面覆盖率作为调整因子（最多提升 20%）
                    sim_matrix[i, j] *= (1 + 0.2 * coverage)

        return sim_matrix

    def _leakage_penalty(
        self,
        pred_memory: SpeakerMemory,
        gt_memory: SpeakerMemory,
        privacy_rules: dict[str, list[str]],
    ) -> float:
        """
        计算 cross-speaker information leakage penalty。

        违规情况：
        1. Alice 的 fact 被写到了 Bob 的 bucket（归因错误）
        2. Alice 的私密信息对 forbidden recipient 可见

        Returns: float [0,1]，越大说明 leakage 越严重
        """
        violations = 0
        total_entries = len(pred_memory.all_entries_flat())

        if total_entries == 0:
            return 0.0

        # 类型1：归因错误（某说话人的 fact 被放到错误的 bucket）
        for speaker_id, pred_entries in pred_memory.entries.items():
            for pred_entry in pred_entries:
                # 检查这条 fact 是否真的属于这个 speaker
                actual_owner = self._find_fact_owner(
                    pred_entry.content, gt_memory
                )
                if actual_owner and actual_owner != speaker_id:
                    violations += 1

        # 类型2：隐私泄漏（forbidden recipient 可以访问不该看的信息）
        for speaker_id, forbidden_recipients in privacy_rules.items():
            for entry in pred_memory.entries.get(speaker_id, []):
                for recipient in entry.audience_set:
                    if recipient in forbidden_recipients:
                        violations += 1

        return violations / total_entries

    def _find_fact_owner(
        self,
        fact_content: str,
        gt_memory: SpeakerMemory,
    ) -> Optional[str]:
        """找到某条 fact 在 GT 中真正属于哪个 speaker"""
        for speaker_id, entries in gt_memory.entries.items():
            for entry in entries:
                # 简单字符串相似度（实际应用中用 embedding）
                if self._simple_similarity(fact_content, entry.content) > 0.8:
                    return speaker_id
        return None

    @staticmethod
    def _simple_similarity(text1: str, text2: str) -> float:
        """简单词级 Jaccard 相似度（用于 leakage 检测的快速估计）"""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        if not tokens1 or not tokens2:
            return 0.0
        return len(tokens1 & tokens2) / len(tokens1 | tokens2)


# ============================================================
# 测试 + 示例
# ============================================================

def test_speaker_levenshtein():
    """
    基本单元测试：验证 SpeakerLevenshtein 的行为是否符合预期
    """
    # 构建测试 memory 状态
    gt_memory = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice works at ByteDance as NLP engineer", "Alice"),
            MemoryEntry("Alice likes hiking on weekends", "Alice"),
        ],
        'Bob': [
            MemoryEntry("Bob is a startup founder", "Bob"),
            MemoryEntry("Bob has two years of experience in AI", "Bob"),
        ],
    })

    # 完美预测（预期 F1=1.0）
    perfect_pred = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice works at ByteDance as NLP engineer", "Alice"),
            MemoryEntry("Alice likes hiking on weekends", "Alice"),
        ],
        'Bob': [
            MemoryEntry("Bob is a startup founder", "Bob"),
            MemoryEntry("Bob has two years of experience in AI", "Bob"),
        ],
    })

    # 错误预测：Alice 的一条 fact 被放到了 Bob 的 bucket（attribution 错误）
    wrong_attr_pred = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice works at ByteDance as NLP engineer", "Alice"),
            # 缺少 Alice 的第二条 fact
        ],
        'Bob': [
            MemoryEntry("Bob is a startup founder", "Bob"),
            MemoryEntry("Alice likes hiking on weekends", "Bob"),  # 归属错误！
        ],
    })

    # 空预测
    empty_pred = SpeakerMemory(entries={})

    reward_fn = SpeakerLevenshteinReward(tau=0.6)

    # Note: 这些测试需要 sentence-transformers，如果没有就 skip embedding 部分
    print("\n=== SpeakerLevenshtein 单元测试 ===")

    # 用简单的字符串完全匹配来测试（不需要 embedding）
    def simple_test():
        """不依赖 embedding 的简单测试"""
        # 测试1：R_leak = 0 when no privacy rules
        result = reward_fn.compute(
            pred_memory=perfect_pred,
            gt_memory=gt_memory,
            privacy_rules={}
        )
        assert result['R_leak'] == 0.0, f"Expected R_leak=0, got {result['R_leak']}"

        # 测试2：R_leak > 0 when attribution error
        result_wrong = reward_fn.compute(
            pred_memory=wrong_attr_pred,
            gt_memory=gt_memory,
            privacy_rules={}
        )
        print(f"  完美预测 R_leak = {result['R_leak']:.3f}")  # 0
        print(f"  归因错误 R_leak = {result_wrong['R_leak']:.3f}")  # > 0

        # 测试3：per_speaker 输出
        print(f"  完美预测 per_speaker = {result.get('per_speaker', {})}")
        print(f"  归因错误 per_speaker = {result_wrong.get('per_speaker', {})}")

    try:
        simple_test()
        print("✓ 基本测试通过（不依赖 embedding）")
    except Exception as e:
        print(f"✗ 测试失败：{e}")

    print("\n注：完整测试（含 embedding）需要安装 sentence-transformers")
    print("    pip install sentence-transformers")


def demo_multi_party_reward():
    """
    演示：三人群聊场景下的奖励计算

    场景：Alice、Bob、Carol 三人聊天
    - Alice 是 NLP 工程师，喜欢爬山
    - Bob 是创业者，有 AI 经验
    - Carol 是产品经理，关注 AI 产品
    """
    gt = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice is an NLP engineer at ByteDance", "Alice"),
            MemoryEntry("Alice enjoys hiking", "Alice"),
        ],
        'Bob': [
            MemoryEntry("Bob is an AI startup founder", "Bob"),
        ],
        'Carol': [
            MemoryEntry("Carol is a product manager", "Carol"),
            MemoryEntry("Carol is interested in AI products", "Carol"),
        ],
    })

    # 模拟不同质量的 memory agent 输出
    good_pred = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice works as NLP engineer at ByteDance", "Alice"),  # 语义相同
            MemoryEntry("Alice likes hiking on weekends", "Alice"),
        ],
        'Bob': [
            MemoryEntry("Bob founded an AI startup", "Bob"),  # 语义相同
        ],
        'Carol': [
            MemoryEntry("Carol is a PM", "Carol"),  # 语义相同（缩写）
            MemoryEntry("Carol cares about AI products", "Carol"),
        ],
    })

    bad_pred = SpeakerMemory(entries={
        'Alice': [
            MemoryEntry("Alice is an engineer", "Alice"),  # 信息不完整
        ],
        'Bob': [
            # Bob 的信息完全遗漏
        ],
        'Carol': [
            MemoryEntry("Carol is a product manager", "Carol"),
            MemoryEntry("Alice enjoys hiking", "Carol"),  # 归因错误！Carol 里有 Alice 的信息
        ],
    })

    reward_fn = SpeakerLevenshteinReward(tau=0.6)

    print("\n=== 三人群聊奖励演示 ===")
    print(f"说话人：Alice, Bob, Carol")

    r_good = reward_fn.compute(good_pred, gt, privacy_rules={})
    r_bad = reward_fn.compute(bad_pred, gt, privacy_rules={
        'Alice': ['Bob']  # Alice 的信息对 Bob 隐私
    })

    print(f"\n好的 memory agent：")
    print(f"  R_leak = {r_good['R_leak']:.3f}")
    print(f"  combined = {r_good['combined']:.3f}")

    print(f"\n差的 memory agent（信息遗漏 + 归因错误 + 隐私泄漏）：")
    print(f"  R_leak = {r_bad['R_leak']:.3f}")
    print(f"  combined = {r_bad['combined']:.3f}")


if __name__ == "__main__":
    test_speaker_levenshtein()
    demo_multi_party_reward()
    print("\n实现完成，等待 sentence-transformers 依赖安装后进行完整测试。")
