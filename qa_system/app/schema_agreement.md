# docs/schema_agreement.md — 与子系统1的 Schema 对齐文档

> **状态**：⚠️ 待确认（当前为假定方案）
> **负责人**：成员E（数据层）+ 子系统1对接人
> **确认后**：更新本文档状态为 ✅ 已确认，并通知成员B修改 query_builder.py 的常量区域

---

## 节点类型

| 节点标签 | 名称 | 备注 |
|---------|------|------|
| 文物 | `Artifact` | 核心节点 |
| 博物馆 | `Museum` | |
| 艺术家 | `Artist` | 主要针对书画类文物 |

## 属性名

| 节点 | 属性含义 | 字段名 | 备注 |
|------|---------|--------|------|
| Artifact | 唯一ID | `object_id` | 主键，如 204498 |
| Artifact | 名称 | `title` | CSV 中为 title |
| Artifact | 类型 | `type` | 如 Ritual Implements |
| Artifact | 材质 | `material` | 如 Green stone |
| Artifact | 尺寸 | `dimensions` | 如 L. 8 x W. 3.4 cm |
| Artifact | 描述 | `description` | |
| Artifact | 朝代 | `dynasty` | 字符串，如 Tang |
| Artifact | 时期 | `period` | 字符串，如 1100–771 BCE |
| Artifact | 详情页URL | `detail_url` | 博物馆原始链接，溯源必需 |
| Artifact | 图片URL | `image_url` | 溯源展示用 |
| Artifact | 馆藏编号 | `accession_number` | 标准引用编号 |
| Museum | 名称 | `name` | 对应 CSV museum 字段 |
| Museum | 城市 | `city` | 从 CSV location 解析 |
| Museum | 国家 | `country` | 从 CSV location 解析 |
| Artist | 名称 | `name` | 对应 CSV artist 字段 |
| Artist | 籍贯 | `artist_province` | |
| Artist | 生平 | `bio` | 若爬取数据无此字段则为空 |

> **相关文物推荐**不通过图谱关系实现，改为基于属性过滤：（根据目前子系统1爬取的数据先这样写）
> 优先匹配 `type` + `material` 相同的文物，其次 `type` + `dynasty`，
> 最后仅 `type` 相同作为兜底。由 `query_builder.py` 生成对应 Cypher。

## 关系类型

| 关系含义 | 关系名 | 方向 | 对应问答需求 |
|---------|--------|------|-------------|
| 文物收藏于博物馆 | `COLLECTED_BY` | (Artifact)→(Museum) | 收藏地查询 |
| 文物由艺术家创作 | `CREATED_BY` | (Artifact)→(Artist) | 作者查询、同作者作品 |



