"""意图与目录的 pydantic 契约（P0 只定义类型，不注册业务意图）。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §5.1、§7.1。
依赖方向：``intent`` 只依赖 pydantic，不依赖 DB / 路由；目录（catalog）与闸（gates）都引用这里的类型。
"""
from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict


class BoundIntent(BaseModel):
    """所有意图参数模型的基类：多余参数一律拒绝（模式闸第一层）。"""

    model_config = ConfigDict(extra="forbid")


class FieldMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str                       # 物理列名（snake_case）
    rdf_name: str                   # 形状/本体属性本地名（camelCase）
    label: str = ""
    data_type: Literal["string", "int", "decimal", "bool", "datetime", "enum"]
    enum: tuple[str, ...] | None = None
    required: bool = False
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None
    fk: str | None = None
    indexed: bool = False
    source: Literal["yaml", "shacl", "mappings", "orm", "projection"] = "yaml"


class EntityMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str                       # 语义名（= ontology_class）
    table: str
    label: str
    top_category: str
    domain: str
    domain_source: Literal["yaml", "yaml_file", "projection"] = "yaml_file"
    ontology_iri: str
    shape_iri: str | None = None
    shape_paths: frozenset[str] = frozenset()   # 形状实际声明的 sh:path 全名
    shape_has_sparql: bool = False
    coverage: Literal["ontology", "projection"] = "ontology"
    fields: dict[str, FieldMeta] = {}
    readonly: bool = True


class Provenance(BaseModel):
    """单行溯源：表 + 记录键 + 本体 IRI，三者缺一即回答失败。"""

    model_config = ConfigDict(frozen=True)

    table: str
    record_key: str
    ontology_iri: str


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    sources: list[Provenance]
    # 空结果的显式原因（如 customer_not_found）；只用于区分"无匹配"与"条件不合法"
    reason: str | None = None


class IntentSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: str
    label: str
    description: str
    entities: list[str]
    primary_entity: str
    params_model: type[BoundIntent]
    defaults: dict[str, Any] = {}
    domains: list[str]
    allowed_roles: frozenset[str]
    output_fields: dict[str, list[str]]
    # 输出列 → 枚举名（枚举名必须在 mappings.json 的 labels 中；供前端本地化展示）
    output_enums: dict[str, str] = {}
    record_key: list[str]
    downlink: str | None = None
    shacl_coverage: Literal["full", "partial", "none"]
    # 外部数据源显式绑定的本体 NodeShape（约束仍只在 ontology/src/shapes.ttl）
    shacl_shape: str | None = None
    # 参数名 → 形状属性名；仅用于把参数映射到形状路径，不承载约束
    shacl_params: dict[str, str] = {}
    provenance_kind: Literal["document", "event", "aggregate"]
    rules: list[str] = []
    formula: str | None = None
    handler: Callable[..., QueryResult]
    read_only: Literal[True] = True
    # 数据来源系统：ERP 走本地 ORM；MES 走跨库只读客户端（默认关闭）
    source_system: Literal["ERP", "MES"] = "ERP"


# P0 不注册意图；P1 的 W1.1 在这里或 intents/__init__.py 填充。
INTENTS: dict[str, IntentSpec] = {}
