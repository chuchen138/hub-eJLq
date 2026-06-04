"""
Semantic Router Implementation
语义路由，基于向量相似度将输入路由到不同的处理分支
"""

import math
from dataclasses import dataclass, field
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
    """计算两个向量的余弦距离"""
    return 1 - cosine_similarity(vec1, vec2)


@dataclass
class Route:
    """路由类"""

    name: str
    """路由名称"""
    references: List[str] = field(default_factory=list)
    """参考文本列表"""
    distance_threshold: float = 0.3
    """距离阈值"""
    description: Optional[str] = None
    """路由描述"""
    metadata: Dict[str, Any] = field(default_factory=dict)
    """元数据"""


@dataclass
class RouteMatch:
    """路由匹配结果"""

    name: Optional[str] = None
    """匹配的路由名称"""
    distance: float = 1.0
    """匹配距离"""
    metadata: Dict[str, Any] = field(default_factory=dict)
    """路由元数据"""


class SemanticRouter:
    """语义路由器"""

    def __init__(
        self,
        name: str = "semantic_router",
        routes: Optional[List[Route]] = None,
    ):
        """
        初始化语义路由器

        Args:
            name: 路由器名称
            routes: 初始路由列表
        """
        self.name = name
        self.routes: List[Route] = routes or []
        self._reference_vectors: Dict[str, List[Tuple[str, List[float]]]] = {}

    def add_route(
        self,
        name: str,
        references: List[str],
        reference_vectors: Optional[List[List[float]]] = None,
        distance_threshold: float = 0.3,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加路由

        Args:
            name: 路由名称
            references: 参考文本列表
            reference_vectors: 可选的参考向量列表（与 references 一一对应）
            distance_threshold: 距离阈值
            description: 路由描述
            metadata: 元数据
        """
        route = Route(
            name=name,
            references=references,
            distance_threshold=distance_threshold,
            description=description,
            metadata=metadata or {},
        )
        self.routes.append(route)

        # 存储参考向量（如果提供）
        if reference_vectors:
            self._reference_vectors[name] = list(zip(references, reference_vectors))

    def add_route_reference(
        self,
        route_name: str,
        reference: str,
        reference_vector: Optional[List[float]] = None,
    ) -> bool:
        """
        为现有路由添加参考

        Args:
            route_name: 路由名称
            reference: 参考文本
            reference_vector: 可选的参考向量

        Returns:
            是否成功添加
        """
        for route in self.routes:
            if route.name == route_name:
                route.references.append(reference)
                if reference_vector:
                    if route_name not in self._reference_vectors:
                        self._reference_vectors[route_name] = []
                    self._reference_vectors[route_name].append((reference, reference_vector))
                return True
        return False

    def remove_route(self, route_name: str) -> bool:
        """
        删除路由

        Args:
            route_name: 路由名称

        Returns:
            是否成功删除
        """
        for i, route in enumerate(self.routes):
            if route.name == route_name:
                del self.routes[i]
                if route_name in self._reference_vectors:
                    del self._reference_vectors[route_name]
                return True
        return False

    def get_route(self, route_name: str) -> Optional[Route]:
        """
        获取路由

        Args:
            route_name: 路由名称

        Returns:
            路由对象或 None
        """
        for route in self.routes:
            if route.name == route_name:
                return route
        return None

    def _classify_single(
        self,
        query_vector: List[float],
        reference_vectors: Dict[str, List[Tuple[str, List[float]]]],
    ) -> RouteMatch:
        """
        分类到单个路由（内部方法）

        Args:
            query_vector: 查询向量
            reference_vectors: 参考向量字典

        Returns:
            最佳匹配
        """
        best_match = RouteMatch(distance=1.0)

        for route in self.routes:
            route_name = route.name
            route_threshold = route.distance_threshold

            if route_name not in reference_vectors:
                continue

            # 找到与查询最接近的参考
            min_distance = 1.0
            for _, ref_vector in reference_vectors[route_name]:
                distance = cosine_distance(query_vector, ref_vector)
                if distance < min_distance:
                    min_distance = distance

            # 检查是否满足阈值
            if min_distance <= route_threshold and min_distance < best_match.distance:
                best_match = RouteMatch(
                    name=route_name,
                    distance=min_distance,
                    metadata=route.metadata,
                )

        return best_match

    def _classify_multi(
        self,
        query_vector: List[float],
        reference_vectors: Dict[str, List[Tuple[str, List[float]]]],
        max_k: int = 5,
    ) -> List[RouteMatch]:
        """
        分类到多个路由（内部方法）

        Args:
            query_vector: 查询向量
            reference_vectors: 参考向量字典
            max_k: 最大返回数量

        Returns:
            匹配列表
        """
        matches: List[RouteMatch] = []

        for route in self.routes:
            route_name = route.name
            route_threshold = route.distance_threshold

            if route_name not in reference_vectors:
                continue

            # 找到与查询最接近的参考
            min_distance = 1.0
            for _, ref_vector in reference_vectors[route_name]:
                distance = cosine_distance(query_vector, ref_vector)
                if distance < min_distance:
                    min_distance = distance

            # 检查是否满足阈值
            if min_distance <= route_threshold:
                matches.append(RouteMatch(
                    name=route_name,
                    distance=min_distance,
                    metadata=route.metadata,
                ))

        # 排序并返回前 k 个
        matches.sort(key=lambda m: m.distance)
        return matches[:max_k]

    def __call__(
        self,
        query_vector: List[float],
    ) -> RouteMatch:
        """
        调用路由分类

        Args:
            query_vector: 查询向量

        Returns:
            最佳匹配
        """
        return self._classify_single(query_vector, self._reference_vectors)

    def route(
        self,
        query_vector: List[float],
    ) -> RouteMatch:
        """
        路由查询

        Args:
            query_vector: 查询向量

        Returns:
            最佳匹配
        """
        return self._classify_single(query_vector, self._reference_vectors)

    def route_many(
        self,
        query_vector: List[float],
        max_k: int = 5,
    ) -> List[RouteMatch]:
        """
        路由查询到多个结果

        Args:
            query_vector: 查询向量
            max_k: 最大返回数量

        Returns:
            匹配列表
        """
        return self._classify_multi(query_vector, self._reference_vectors, max_k)

    def set_reference_vectors(
        self,
        route_name: str,
        reference_vectors: List[Tuple[str, List[float]]],
    ) -> bool:
        """
        设置路由的参考向量

        Args:
            route_name: 路由名称
            reference_vectors: (参考文本, 参考向量) 列表

        Returns:
            是否成功设置
        """
        route = self.get_route(route_name)
        if not route:
            return False

        self._reference_vectors[route_name] = reference_vectors
        return True

    @property
    def route_names(self) -> List[str]:
        """获取所有路由名称"""
        return [route.name for route in self.routes]

    def clear(self) -> None:
        """清空所有路由"""
        self.routes.clear()
        self._reference_vectors.clear()


# 使用示例
if __name__ == "__main__":
    # 创建路由器
    router = SemanticRouter()

    # 添加路由
    router.add_route(
        name="weather",
        references=[
            "What's the weather like?",
            "Is it going to rain?",
            "Temperature today",
        ],
        distance_threshold=0.4,
        description="Weather related queries",
        metadata={"handler": "weather_api"},
    )

    # 设置参考向量（实际中由嵌入模型生成）
    router.set_reference_vectors(
        "weather",
        [
            ("What's the weather like?", [0.1, 0.2, 0.3]),
            ("Is it going to rain?", [0.15, 0.25, 0.35]),
            ("Temperature today", [0.12, 0.22, 0.32]),
        ],
    )

    router.add_route(
        name="time",
        references=[
            "What time is it?",
            "Current time",
            "What day is today?",
        ],
        distance_threshold=0.4,
        description="Time related queries",
        metadata={"handler": "time_api"},
    )

    router.set_reference_vectors(
        "time",
        [
            ("What time is it?", [-0.1, -0.2, -0.3]),
            ("Current time", [-0.15, -0.25, -0.35]),
            ("What day is today?", [-0.12, -0.22, -0.32]),
        ],
    )

    # 测试路由
    print("测试路由:")
    match = router.route([0.14, 0.24, 0.34])
    print(f"最佳匹配: {match.name}, 距离: {match.distance:.4f}")
    print()

    # 测试多匹配
    print("测试多匹配:")
    matches = router.route_many([0.0, 0.0, 0.0], max_k=2)
    for m in matches:
        print(f"匹配: {m.name}, 距离: {m.distance:.4f}")
