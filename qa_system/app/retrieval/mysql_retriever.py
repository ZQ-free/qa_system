"""
app/retrieval/mysql_retriever.py — MySQL 真实数据检索器

职责：
  替代 MockRetriever，从真实 MySQL 数据库中检索文物数据。
  接口与 MockRetriever 完全相同，QAEngine 无缝切换。

关键设计：
  retrieve(cypher, params) 接口保持不变，但内部不执行 Cypher，
  而是从 cypher 参数中推断意图，然后执行对应的 MySQL 查询。
  返回结果的字段名与 Mock 数据完全一致，answer_builder.py 无需改动。
"""

from app.core.intent_types import Intent
from app.db.mysql_client import MySQLClient


class MySQLRetriever:

    async def retrieve(self, cypher: str, params: dict) -> list:
        intent = self._infer_intent(cypher)
        entity = params.get("entity", "")

        if not entity and intent not in {Intent.DYNASTY_ARTIFACTS}:
            return []

        handler = self._HANDLERS.get(intent)
        if handler:
            return await handler(self, entity)
        return []

    async def _handle_location(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "museum_name": r.get("museum", ""),
                "city": self._extract_city(r.get("location", "")),
                "country": self._extract_country(r.get("location", "")),
                "image_url": r.get("image_url"),
                "accession_number": r.get("accession_number"),
            }
            for r in rows
        ] if rows else []

    async def _handle_period(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        if not rows:
            rows = await MySQLClient.search_by_dynasty(entity, limit=5)
            if not rows:
                return []
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "dynasty_name": r.get("dynasty", ""),
                "period": r.get("period", ""),
                "period_start_year": r.get("period_start_year"),
                "period_end_year": r.get("period_end_year"),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ]

    async def _handle_material(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "material": r.get("material", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ] if rows else []

    async def _handle_type(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "artifact_type": r.get("type", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ] if rows else []

    async def _handle_introduction(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "description": r.get("description", ""),
                "artifact_type": r.get("type", ""),
                "material": r.get("material", ""),
                "dynasty_name": r.get("dynasty", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ] if rows else []

    async def _handle_author(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        if not rows:
            return []
        result = []
        for r in rows:
            if r.get("artist"):
                result.append({
                    "artifact_name": r.get("title", ""),
                    "object_id": r.get("object_id", ""),
                    "detail_url": r.get("detail_url", ""),
                    "artist_name": r.get("artist", ""),
                    "museum_name": r.get("museum", ""),
                })
        return result

    async def _handle_biography(self, entity: str) -> list:
        rows = await MySQLClient.search_by_artist(entity, limit=5)
        if not rows:
            return []
        first = rows[0]
        return [
            {
                "artist_name": first.get("artist", entity),
                "artist_bio": first.get("artist_bio", ""),
                "artist_birth": first.get("artist_birth", ""),
                "artist_death": first.get("artist_death", ""),
                "artist_province": first.get("artist_province", ""),
            }
        ]

    async def _handle_other_works(self, entity: str) -> list:
        rows = await MySQLClient.search_by_artist(entity, limit=10)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "artifact_type": r.get("type", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ]

    async def _handle_dynasty(self, entity: str) -> list:
        rows = await MySQLClient.search_by_dynasty(entity, limit=10)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "artifact_type": r.get("type", ""),
                "dynasty_name": r.get("dynasty", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ]

    async def _handle_dimensions(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=5)
        return [
            {
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "dimensions": r.get("dimensions", ""),
                "museum_name": r.get("museum", ""),
            }
            for r in rows
        ] if rows else []

    async def _handle_recommend(self, entity: str) -> list:
        rows = await MySQLClient.search_by_title(entity, limit=1)
        if not rows:
            return []
        target = rows[0]
        similar = await MySQLClient.get_similar_artifacts(
            artifact_type=target.get("type", ""),
            material=target.get("material", "") or "",
            dynasty=target.get("dynasty", "") or "",
            exclude_object_id=target.get("object_id", ""),
            limit=10,
        )
        return [
            {
                "title": r.get("title", ""),
                "artifact_name": r.get("title", ""),
                "object_id": r.get("object_id", ""),
                "detail_url": r.get("detail_url", ""),
                "type": r.get("type", ""),
                "artifact_type": r.get("type", ""),
                "material": r.get("material", ""),
                "dynasty": r.get("dynasty", ""),
                "dynasty_name": r.get("dynasty", ""),
                "museum_name": r.get("museum", ""),
                "museum": r.get("museum", ""),
                "match_reason": r.get("match_reason", ""),
            }
            for r in similar
        ]

    @staticmethod
    def _extract_city(location: str) -> str:
        if not location:
            return ""
        parts = location.split(",")
        return parts[0].strip() if parts else ""

    @staticmethod
    def _extract_country(location: str) -> str:
        if not location:
            return ""
        parts = location.split(",")
        return parts[-1].strip() if len(parts) > 1 else ""

    @staticmethod
    def _infer_intent(cypher: str) -> str:
        c = cypher.lower()
        if "biography" in c or "artist_bio" in c:
            return Intent.AUTHOR_BIOGRAPHY
        if "dimensions" in c:
            return Intent.ARTIFACT_DIMENSIONS
        if "description" in c:
            return Intent.ARTIFACT_INTRODUCTION
        if "match_reason" in c or "similar" in c:
            return Intent.ARTIFACT_RECOMMEND
        if "created_by" in c or "other_works" in c:
            return Intent.AUTHOR_OTHER_WORKS
        if "dynasty_name" in c and ("artifact_type" in c or "type" in c):
            return Intent.DYNASTY_ARTIFACTS
        if "dynasty" in c:
            return Intent.ARTIFACT_PERIOD
        if "artifact_type" in c or ("type" in c and "return" in c):
            return Intent.ARTIFACT_TYPE
        if "material" in c:
            return Intent.ARTIFACT_MATERIAL
        if "artist_name" in c:
            return Intent.ARTIFACT_AUTHOR
        return Intent.ARTIFACT_LOCATION

    _HANDLERS = {
        Intent.ARTIFACT_LOCATION: _handle_location,
        Intent.ARTIFACT_PERIOD: _handle_period,
        Intent.ARTIFACT_MATERIAL: _handle_material,
        Intent.ARTIFACT_TYPE: _handle_type,
        Intent.ARTIFACT_INTRODUCTION: _handle_introduction,
        Intent.ARTIFACT_AUTHOR: _handle_author,
        Intent.AUTHOR_BIOGRAPHY: _handle_biography,
        Intent.AUTHOR_OTHER_WORKS: _handle_other_works,
        Intent.DYNASTY_ARTIFACTS: _handle_dynasty,
        Intent.ARTIFACT_DIMENSIONS: _handle_dimensions,
        Intent.ARTIFACT_RECOMMEND: _handle_recommend,
    }
