"""
Semantic Cache Implementation
基于向量相似度的语义缓存，支持 LLM 响应缓存
"""

import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦距离 (1 - cosine_similarity)"""
    return 1 - cosine_similarity(vec1, vec2)


class SemanticCache:
    """语义缓存类，基于向量相似度查找缓存"""

    def __init__(
        self,
        name: str = "semantic_cache",
        distance_threshold: float = 0.1,
        ttl: Optional[int] = None,
    ):
        """
        初始化语义缓存

        Args:
            name: 缓存名称
            distance_threshold: 相似度阈值（余弦距离），越小越严格
            ttl: 缓存过期时间
        """
        self.name = name
        self.distance_threshold = distance_threshold
        self.ttl = ttl
        self._storage: Dict[str, Dict] = {}  # key -> entry
        self._vectors: Dict[str, List[float]] = {}  # key -> vector

    def _make_entry_id(self, prompt: str, filters: Optional[Dict] = None) -> str:
        """生成确定性条目 ID"""
        combined = prompt + (str(filters) if filters else "")
        return hashlib.md5(combined.encode()).hexdigest()

    def set_threshold(self, distance_threshold: float) -> None:
        """设置相似度阈值"""
        self.distance_threshold = distance_threshold

    def check(
        self,
        prompt: Optional[str] = None,
        vector: Optional[List[float]] = None,
        num_results: int = 1,
        distance_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        检查缓存中是否有相似的查询

        Args:
            prompt: 查询文本（如果提供了 vector 则可以省略）
            vector: 查询向量（如果提供了 prompt 则可以省略）
            num_results: 返回结果数量
            distance_threshold: 可选覆盖默认阈值

        Returns:
            匹配的缓存条目列表
        """
        if vector is None:
            raise ValueError("必须提供 vector（在实际实现中会由 prompt 生成）")

        threshold = distance_threshold or self.distance_threshold

        # 计算与所有缓存向量的距离
        matches: List[Tuple[float, Dict]] = []
        for key, entry in self._storage.items():
            cached_vector = self._vectors[key]
            distance = cosine_distance(vector, cached_vector)
            if distance <= threshold:
                matches.append((distance, entry))

        # 按距离排序并返回
        matches.sort(key=lambda x: x[0])
        results = []
        for distance, entry in matches[:num_results]:
            result = entry.copy()
            result["distance"] = distance
            results.append(result)

        return results

    def store(
        self,
        prompt: str,
        response: str,
        vector: List[float],
        metadata: Optional[Dict] = None,
        filters: Optional[Dict] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        存储查询-响应对

        Args:
            prompt: 用户查询
            response: LLM 响应
            vector: prompt 的嵌入向量
            metadata: 可选元数据
            filters: 可选过滤条件
            ttl: 可选覆盖默认过期时间

        Returns:
            存储的键
        """
        entry_id = self._make_entry_id(prompt, filters)
        key = f"{self.name}:{entry_id}"

        entry = {
            "entry_id": entry_id,
            "prompt": prompt,
            "response": response,
            "metadata": metadata,
            "filters": filters,
        }

        self._storage[key] = entry
        self._vectors[key] = vector
        return key

    def drop(self, key: str) -> None:
        """删除指定缓存条目"""
        if key in self._storage:
            del self._storage[key]
        if key in self._vectors:
            del self._vectors[key]

    def clear(self) -> None:
        """清空所有缓存"""
        self._storage.clear()
        self._vectors.clear()

    def get_all(self) -> List[Dict]:
        """获取所有缓存条目"""
        return list(self._storage.values())


# 使用示例
if __name__ == "__main__":
    cache = SemanticCache(distance_threshold=0.3)

    # 存储一些示例
    cache.store(
        prompt="What is the capital of France?",
        response="Paris",
        vector=[0.1, 0.2, 0.3, 0.4, 0.5],
    )

    cache.store(
        prompt="Tell me about Paris",
        response="Paris is the capital of France...",
        vector=[0.15, 0.25, 0.35, 0.45, 0.55],
    )

    cache.store(
        prompt="What is the capital of Germany?",
        response="Berlin",
        vector=[-0.1, -0.2, -0.3, -0.4, -0.5],
    )

    # 检查相似查询
    print("检查相似查询:")
    results = cache.check(vector=[0.12, 0.22, 0.32, 0.42, 0.52], num_results=2)
    for result in results:
        print(f"距离: {result['distance']:.4f}")
        print(f"Prompt: {result['prompt']}")
        print(f"Response: {result['response']}")
        print()
