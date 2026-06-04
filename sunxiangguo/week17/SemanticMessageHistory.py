"""
Semantic Message History Implementation
语义化聊天历史，支持向量相似度检索历史消息
"""

import math
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦距离"""
    return 1 - cosine_similarity(vec1, vec2)


class ChatMessage:
    """聊天消息类"""

    def __init__(
        self,
        role: str,
        content: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict] = None,
        session_tag: Optional[str] = None,
    ):
        """
        初始化聊天消息

        Args:
            role: 消息角色（user, assistant, system 等）
            content: 消息内容
            vector: 可选嵌入向量
            metadata: 可选元数据
            session_tag: 会话标签
        """
        self.id = str(uuid.uuid4())
        self.role = role
        self.content = content
        self.vector = vector
        self.metadata = metadata or {}
        self.session_tag = session_tag
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "session_tag": self.session_tag,
            "timestamp": self.timestamp,
        }


class SemanticMessageHistory:
    """语义化聊天历史类"""

    def __init__(
        self,
        name: str = "chat_history",
        session_tag: Optional[str] = None,
        distance_threshold: float = 0.3,
    ):
        """
        初始化语义化聊天历史

        Args:
            name: 历史名称
            session_tag: 默认会话标签
            distance_threshold: 相似度阈值
        """
        self.name = name
        self.session_tag = session_tag or str(uuid.uuid4())
        self.distance_threshold = distance_threshold
        self._messages: List[ChatMessage] = []

    def add_message(
        self,
        role: str,
        content: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict] = None,
        session_tag: Optional[str] = None,
    ) -> str:
        """
        添加单条消息

        Args:
            role: 消息角色
            content: 消息内容
            vector: 可选嵌入向量
            metadata: 可选元数据
            session_tag: 可选覆盖默认会话标签

        Returns:
            消息 ID
        """
        message = ChatMessage(
            role=role,
            content=content,
            vector=vector,
            metadata=metadata,
            session_tag=session_tag or self.session_tag,
        )
        self._messages.append(message)
        return message.id

    def add_messages(
        self,
        messages: List[Dict[str, Any]],
        session_tag: Optional[str] = None,
    ) -> List[str]:
        """
        批量添加消息

        Args:
            messages: 消息字典列表，每个包含 role 和 content
            session_tag: 可选覆盖默认会话标签

        Returns:
            消息 ID 列表
        """
        ids = []
        for msg in messages:
            msg_id = self.add_message(
                role=msg["role"],
                content=msg["content"],
                vector=msg.get("vector"),
                metadata=msg.get("metadata"),
                session_tag=session_tag,
            )
            ids.append(msg_id)
        return ids

    def store(
        self,
        prompt: str,
        response: str,
        prompt_vector: Optional[List[float]] = None,
        response_vector: Optional[List[float]] = None,
        session_tag: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        存储一组对话（用户提示 + AI 响应）

        Args:
            prompt: 用户提示
            response: AI 响应
            prompt_vector: 提示的嵌入向量
            response_vector: 响应的嵌入向量
            session_tag: 可选会话标签

        Returns:
            (prompt_id, response_id)
        """
        prompt_id = self.add_message(
            role="user",
            content=prompt,
            vector=prompt_vector,
            session_tag=session_tag,
        )
        response_id = self.add_message(
            role="assistant",
            content=response,
            vector=response_vector,
            session_tag=session_tag,
        )
        return prompt_id, response_id

    def get_recent(
        self,
        top_k: int = 5,
        session_tag: Optional[str] = None,
        role: Optional[Union[str, List[str]]] = None,
    ) -> List[Dict]:
        """
        获取最近的消息

        Args:
            top_k: 返回消息数量
            session_tag: 可选会话过滤
            role: 可选角色过滤

        Returns:
            消息字典列表
        """
        filtered = self._filter_messages(session_tag, role)
        # 按时间倒序取最近的
        filtered_sorted = sorted(filtered, key=lambda m: m.timestamp, reverse=True)
        return [m.to_dict() for m in filtered_sorted[:top_k]]

    def get_relevant(
        self,
        query_vector: List[float],
        top_k: int = 5,
        session_tag: Optional[str] = None,
        role: Optional[Union[str, List[str]]] = None,
        distance_threshold: Optional[float] = None,
    ) -> List[Dict]:
        """
        获取语义相关的消息

        Args:
            query_vector: 查询向量
            top_k: 返回消息数量
            session_tag: 可选会话过滤
            role: 可选角色过滤
            distance_threshold: 可选覆盖默认阈值

        Returns:
            相关消息字典列表，按相似度排序
        """
        filtered = self._filter_messages(session_tag, role)
        threshold = distance_threshold or self.distance_threshold

        # 计算相似度
        matches: List[Tuple[float, ChatMessage]] = []
        for message in filtered:
            if message.vector is not None:
                distance = cosine_distance(query_vector, message.vector)
                if distance <= threshold:
                    matches.append((distance, message))

        # 排序并返回
        matches.sort(key=lambda x: x[0])
        results = []
        for distance, message in matches[:top_k]:
            msg_dict = message.to_dict()
            msg_dict["distance"] = distance
            results.append(msg_dict)

        return results

    def _filter_messages(
        self,
        session_tag: Optional[str] = None,
        role: Optional[Union[str, List[str]]] = None,
    ) -> List[ChatMessage]:
        """过滤消息"""
        filtered = self._messages

        if session_tag:
            filtered = [m for m in filtered if m.session_tag == session_tag]

        if role:
            if isinstance(role, str):
                role = [role]
            filtered = [m for m in filtered if m.role in role]

        return filtered

    def get_all(
        self,
        session_tag: Optional[str] = None,
    ) -> List[Dict]:
        """获取所有消息"""
        filtered = self._filter_messages(session_tag)
        return [m.to_dict() for m in filtered]

    def drop(self, message_id: str) -> bool:
        """删除指定消息"""
        for i, message in enumerate(self._messages):
            if message.id == message_id:
                del self._messages[i]
                return True
        return False

    def clear(self, session_tag: Optional[str] = None) -> None:
        """清空消息"""
        if session_tag:
            self._messages = [
                m for m in self._messages if m.session_tag != session_tag
            ]
        else:
            self._messages.clear()


# 使用示例
if __name__ == "__main__":
    history = SemanticMessageHistory()

    # 添加对话
    history.store(
        prompt="What is machine learning?",
        response="Machine learning is a field of AI...",
        prompt_vector=[0.1, 0.2, 0.3, 0.4, 0.5],
        response_vector=[0.15, 0.25, 0.35, 0.45, 0.55],
    )

    history.store(
        prompt="How do neural networks work?",
        response="Neural networks are inspired by the human brain...",
        prompt_vector=[-0.1, -0.2, -0.3, -0.4, -0.5],
        response_vector=[-0.15, -0.25, -0.35, -0.45, -0.55],
    )

    # 获取最近消息
    print("最近消息:")
    recent = history.get_recent(top_k=2)
    for msg in recent:
        print(f"{msg['role']}: {msg['content']}")
    print()

    # 获取相关消息
    print("相关消息:")
    relevant = history.get_relevant(query_vector=[0.12, 0.22, 0.32, 0.42, 0.52])
    for msg in relevant:
        print(f"距离: {msg['distance']:.4f}")
        print(f"{msg['role']}: {msg['content']}")
        print()
