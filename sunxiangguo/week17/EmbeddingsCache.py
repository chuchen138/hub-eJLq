"""
Embeddings Cache Implementation
基于 Redis 的嵌入向量缓存，支持精确匹配和批量操作
"""

import hashlib
import json
from typing import Any, Iterable, List, Optional, Union


class EmbeddingsCache:
    """嵌入向量缓存类，用于存储和检索文本嵌入"""

    def __init__(
        self,
        name: str = "embedcache",
        redis_url: str = "redis://localhost:6379",
        ttl: Optional[int] = None,
    ):
        """
        初始化嵌入缓存

        Args:
            name: 缓存名称，用于构建 Redis 键前缀
            redis_url: Redis 连接 URL
            ttl: 缓存条目默认过期时间（秒）
        """
        self.name = name
        self.redis_url = redis_url
        self.ttl = ttl
        self._storage = {}  # 模拟 Redis 存储

    def _make_entry_id(self, content: Union[bytes, str], model_name: str) -> str:
        """
        生成确定性条目 ID

        Args:
            content: 原始内容
            model_name: 嵌入模型名称

        Returns:
            哈希 ID
        """
        if isinstance(content, bytes):
            content = content.hex()
        combined = f"{content}:{model_name}"
        return hashlib.md5(combined.encode()).hexdigest()

    def _make_key(self, entry_id: str) -> str:
        """构建 Redis 键"""
        return f"{self.name}:{entry_id}"

    def get(self, content: Union[bytes, str], model_name: str) -> Optional[dict]:
        """
        获取嵌入向量

        Args:
            content: 原始内容
            model_name: 嵌入模型名称

        Returns:
            缓存条目，如果不存在则返回 None
        """
        key = self._make_key(self._make_entry_id(content, model_name))
        return self._storage.get(key)

    def mget(
        self, contents: Iterable[Union[bytes, str]], model_name: str
    ) -> List[Optional[dict]]:
        """
        批量获取嵌入向量

        Args:
            contents: 内容列表
            model_name: 嵌入模型名称

        Returns:
            缓存条目列表
        """
        return [self.get(content, model_name) for content in contents]

    def set(
        self,
        content: Union[bytes, str],
        model_name: str,
        embedding: List[float],
        metadata: Optional[dict] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """
        存储嵌入向量

        Args:
            content: 原始内容
            model_name: 嵌入模型名称
            embedding: 嵌入向量
            metadata: 可选元数据
            ttl: 可选覆盖默认过期时间

        Returns:
            存储的 Redis 键
        """
        entry_id = self._make_entry_id(content, model_name)
        key = self._make_key(entry_id)

        entry = {
            "entry_id": entry_id,
            "content": content,
            "model_name": model_name,
            "embedding": embedding,
            "metadata": metadata,
        }

        self._storage[key] = entry
        return key

    def mset(
        self,
        items: List[dict],
        ttl: Optional[int] = None,
    ) -> List[str]:
        """
        批量存储嵌入向量

        Args:
            items: 条目列表，每个条目包含 content, model_name, embedding, metadata
            ttl: 可选覆盖默认过期时间

        Returns:
            存储的 Redis 键列表
        """
        keys = []
        for item in items:
            key = self.set(
                content=item["content"],
                model_name=item["model_name"],
                embedding=item["embedding"],
                metadata=item.get("metadata"),
                ttl=ttl,
            )
            keys.append(key)
        return keys

    def exists(self, content: Union[bytes, str], model_name: str) -> bool:
        """
        检查嵌入是否存在

        Args:
            content: 原始内容
            model_name: 嵌入模型名称

        Returns:
            是否存在
        """
        return self.get(content, model_name) is not None

    def drop(self, content: Union[bytes, str], model_name: str) -> None:
        """
        删除嵌入

        Args:
            content: 原始内容
            model_name: 嵌入模型名称
        """
        key = self._make_key(self._make_entry_id(content, model_name))
        if key in self._storage:
            del self._storage[key]

    def clear(self) -> None:
        """清空所有缓存"""
        self._storage.clear()


# 使用示例
if __name__ == "__main__":
    cache = EmbeddingsCache()

    # 存储嵌入
    cache.set(
        content="Hello world",
        model_name="text-embedding-ada-002",
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5],
        metadata={"source": "example"},
    )

    # 获取嵌入
    result = cache.get("Hello world", "text-embedding-ada-002")
    print("获取结果:", result)

    # 检查存在
    print("是否存在:", cache.exists("Hello world", "text-embedding-ada-002"))

    # 批量操作
    cache.mset([
        {
            "content": "First text",
            "model_name": "text-embedding-ada-002",
            "embedding": [1.0, 2.0, 3.0],
        },
        {
            "content": "Second text",
            "model_name": "text-embedding-ada-002",
            "embedding": [4.0, 5.0, 6.0],
        },
    ])

    results = cache.mget(["First text", "Second text"], "text-embedding-ada-002")
    print("批量获取结果:", results)
