"""本体检索服务（A1）：进程内只读加载 TTL，提供实体描述/词法检索/规则/SPARQL。

设计依据：``01-系统设计-DIERP-AI原生化.md`` §5.5、§5.6。
- 语义图 = erp-ontology.ttl + security.ttl + rules.swrl（**不含** demo.ttl）；
- 形状图 = shapes.ttl；
- SPARQL 只在 schema 图执行（语义图剔除 ``:JwtConfig`` 三元组），避免 JWT 配置外泄。
本服务不做推理，也不访问业务数据库。
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

from backend.ontology.registry import ROOT

NS = "https://dierp.local/ontology/erp/v1#"
SWRL = "http://www.w3.org/2003/11/swrl#"
SH = "http://www.w3.org/ns/shacl#"

ERP_TTL = ROOT / "ontology" / "src" / "erp-ontology.ttl"
SHAPES_TTL = ROOT / "ontology" / "src" / "shapes.ttl"
SECURITY_TTL = ROOT / "ontology" / "src" / "security.ttl"
RULES_SWRL = ROOT / "ontology" / "src" / "rules.swrl"
MAPPINGS_JSON = ROOT / "ontology" / "src" / "mappings.json"

# 规则 → 使用它的意图（P0 只有元数据，P1 由意图注册表校验一致性）
RULE_USAGE: dict[str, list[str]] = {
    "R1": ["purchase_suggestions"],
    "R2": ["open_mrp_exceptions"],
    "R3": ["kitting_shortage"],
}

_PREFIXES: list[tuple[str, str]] = [
    (NS, "erp:"),
    ("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdf:"),
    ("http://www.w3.org/2000/01/rdf-schema#", "rdfs:"),
    ("http://www.w3.org/2002/07/owl#", "owl:"),
    ("http://www.w3.org/2001/XMLSchema#", "xsd:"),
    ("http://www.w3.org/ns/shacl#", "sh:"),
    (SWRL, "swrl:"),
]

_FORBIDDEN_KEYWORDS = (
    "SERVICE", "FROM", "LOAD", "INSERT", "DELETE", "DROP", "CLEAR",
    "CREATE", "ADD", "MOVE", "COPY", "WITH",
)
_ALLOWED_LEADING = ("SELECT", "ASK", "DESCRIBE")
_LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)\s*;?\s*$", re.IGNORECASE)
_PREFIX_LINE_RE = re.compile(r"^\s*PREFIX\s+\S+\s+<[^>]+>\s*$", re.IGNORECASE)


class OntologySourceError(RuntimeError):
    """本体源文件缺失或不可解析时抛出，由路由层转为明确错误而非 500 堆栈。"""


def _local(iri: Any) -> str:
    text = str(iri)
    return text.split("#")[-1] if "#" in text else text.rsplit("/", 1)[-1]


def _shorten(value: Any) -> str:
    text = str(value)
    for full, short in _PREFIXES:
        if text.startswith(full):
            return short + text[len(full):]
    return text


class OntologyService:
    """单例语义图服务；首次调用时加载，之后复用。"""

    def __init__(self) -> None:
        self.semantic: Graph | None = None
        self.shapes: Graph | None = None
        self.schema: Graph | None = None
        self.mappings: dict[str, list[str]] = {}
        self.enum_labels: dict[str, dict[str, str]] = {}
        self.load_count = 0

    # ── 加载 ──────────────────────────────────────────────
    def load(self) -> None:
        missing = [
            str(p) for p in (ERP_TTL, SHAPES_TTL, SECURITY_TTL, RULES_SWRL, MAPPINGS_JSON)
            if not p.is_file()
        ]
        if missing:
            raise OntologySourceError("本体源文件缺失: " + ", ".join(missing))

        try:
            semantic = Graph()
            semantic.parse(ERP_TTL, format="turtle")
            semantic.parse(SECURITY_TTL, format="turtle")
            semantic.parse(RULES_SWRL, format="n3")
            shapes = Graph()
            shapes.parse(SHAPES_TTL, format="turtle")
            mappings = json.loads(MAPPINGS_JSON.read_text(encoding="utf-8"))
        except OntologySourceError:
            raise
        except Exception as exc:  # 解析失败同样按"源不可用"处理
            raise OntologySourceError(f"本体源解析失败: {exc}") from exc

        schema = Graph()
        for triple in semantic:
            schema.add(triple)
        jwt = URIRef(NS + "JwtConfig")
        for triple in list(schema.triples((jwt, None, None))):
            schema.remove(triple)

        self.semantic = semantic
        self.shapes = shapes
        self.schema = schema
        self.mappings = mappings
        self.enum_labels = {
            str(name): {str(code): str(label) for code, label in values.items()}
            for name, values in (mappings.get("labels") or {}).items()
            if isinstance(values, dict)
        }
        self.load_count += 1

    def _ensure(self) -> None:
        if self.semantic is None:
            self.load()

    def ensure_loaded(self) -> None:
        """公开的懒加载入口：调用方直接读 ``semantic/shapes/schema`` 前先调用。

        单例可能在测试重置或进程冷启动后处于未加载状态；直接把 ``shapes``
        （可能为 ``None``）传给 pyshacl，会退化成本图自校验而静默通过。
        """
        self._ensure()

    def enum_label(self, enum_name: str, code: str, default: str = "未知") -> str:
        """枚举码 → 中文标签；标签唯一来源是 mappings.json 的 labels 段。"""
        self._ensure()
        return self.enum_labels.get(enum_name, {}).get(str(code), default)

    # ── 描述 ──────────────────────────────────────────────
    def _class_uri(self, name: str) -> URIRef | None:
        self._ensure()
        assert self.semantic is not None
        for candidate in (URIRef(NS + name), URIRef(name)):
            if (candidate, RDF.type, OWL.Class) in self.semantic:
                return candidate
        return None

    def _top_category(self, cls: URIRef) -> str | None:
        assert self.semantic is not None
        current = cls
        seen: set[URIRef] = set()
        while current not in seen:
            seen.add(current)
            parents = list(self.semantic.objects(current, RDFS.subClassOf))
            if not parents:
                return _local(current)
            current = parents[0]
        return None

    def describe(self, name: str) -> dict[str, Any]:
        cls = self._class_uri(name)
        if cls is None:
            raise KeyError(name)
        assert self.semantic is not None and self.shapes is not None

        shape = next(self.shapes.subjects(URIRef(SH + "targetClass"), cls), None)

        properties: list[dict[str, Any]] = []
        seen: set[str] = set()
        if shape is not None:
            for prop in self.shapes.objects(shape, URIRef(SH + "property")):
                path = self.shapes.value(prop, URIRef(SH + "path"))
                if path is None:
                    continue
                prop_name = _local(path)
                if prop_name in seen:
                    continue
                seen.add(prop_name)
                values = self.shapes.value(prop, URIRef(SH + "in"))
                min_count = self.shapes.value(prop, URIRef(SH + "minCount"))
                prop_label = self.semantic.value(path, RDFS.label)
                prop_range = self.semantic.value(path, RDFS.range)
                properties.append({
                    "name": prop_name,
                    "label": str(prop_label) if prop_label is not None else None,
                    "kind": "object"
                    if (path, RDF.type, OWL.ObjectProperty) in self.semantic else "datatype",
                    "range": _local(prop_range) if prop_range is not None else None,
                    "enum": (
                        [str(v) for v in Collection(self.shapes, values)]
                        if values is not None else None
                    ),
                    "required": bool(min_count is not None and int(min_count) > 0),
                })
        properties.sort(key=lambda item: item["name"])

        label = self.semantic.value(cls, RDFS.label)
        comment = self.semantic.value(cls, RDFS.comment)
        return {
            "name": _local(cls),
            "label": str(label) if label is not None else None,
            "comment": str(comment) if comment is not None else None,
            "top_category": self._top_category(cls),
            "ontology_iri": NS,
            "shape": str(shape) if shape is not None else None,
            "properties": properties,
        }

    # ── 检索 ──────────────────────────────────────────────
    def search(self, q: str, limit: int = 20) -> list[dict[str, Any]]:
        self._ensure()
        assert self.semantic is not None
        needle = (q or "").strip().lower()
        if not needle:
            return []

        best: dict[tuple[str, str], dict[str, Any]] = {}

        def offer(kind: str, name: str, label: str | None, score: int) -> None:
            key = (kind, name)
            current = best.get(key)
            if current is None or score > current["score"]:
                best[key] = {"name": name, "label": label, "kind": kind, "score": score}

        for cls in self.semantic.subjects(RDF.type, OWL.Class):
            name = _local(cls)
            label = self.semantic.value(cls, RDFS.label)
            comment = self.semantic.value(cls, RDFS.comment)
            if label and needle in str(label).lower():
                offer("class", name, str(label), 3)
            elif comment and needle in str(comment).lower():
                offer("class", name, str(label) if label else None, 2)
            elif needle in name.lower():
                offer("class", name, str(label) if label else None, 1)

        for prop in self.semantic.subjects(RDF.type, OWL.DatatypeProperty):
            name = _local(prop)
            label = self.semantic.value(prop, RDFS.label)
            if label and needle in str(label).lower():
                offer("property", name, str(label), 3)
            elif needle in name.lower():
                offer("property", name, str(label) if label else None, 1)

        for enum_name, codes in self.mappings.items():
            if not isinstance(codes, list):
                continue
            if needle in enum_name.lower():
                offer("enum", enum_name, None, 1)
            for code in codes:
                if needle in str(code).lower():
                    offer("enum", enum_name, None, 1)
                    break

        items = sorted(best.values(), key=lambda item: (-item["score"], item["kind"], item["name"]))
        return items[: max(0, limit)]

    # ── 规则元数据 ────────────────────────────────────────
    def rules(self) -> list[dict[str, Any]]:
        self._ensure()
        assert self.semantic is not None
        try:
            results: list[dict[str, Any]] = []
            for rule in self.semantic.subjects(RDF.type, URIRef(SWRL + "Imp")):
                label = self.semantic.value(rule, RDFS.label)
                if label is None:
                    continue
                text = str(label).strip()
                match = re.match(r"^(R\d+)\s+(.*)$", text)
                rule_id, title = (match.group(1), match.group(2)) if match else (text, text)
                results.append({
                    "id": rule_id,
                    "label": title,
                    "used_by": RULE_USAGE.get(rule_id, []),
                })
            return sorted(results, key=lambda item: item["id"])
        except Exception:
            return []

    # ── 受限 SPARQL ───────────────────────────────────────
    @staticmethod
    def validate_sparql(query: str, limit: int) -> str:
        text = (query or "").strip().rstrip(";").strip()
        if not text:
            raise ValueError("SPARQL 不能为空")

        body = "\n".join(
            line for line in text.splitlines() if not _PREFIX_LINE_RE.match(line)
        ).strip()
        leading = body.split(None, 1)[0].upper() if body else ""
        if leading not in _ALLOWED_LEADING:
            raise ValueError("只允许 SELECT / ASK / DESCRIBE 查询")

        upper = body.upper()
        for keyword in _FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", upper):
                raise ValueError(f"查询包含被禁止的关键字: {keyword}")

        existing = _LIMIT_RE.search(body)
        if existing:
            if int(existing.group(1)) > 500:
                raise ValueError("LIMIT 不得超过 500")
            return body
        effective = max(1, min(limit, 200))
        return f"{body}\nLIMIT {effective}"

    def sparql(self, query: str, limit: int = 200) -> list[dict[str, str]]:
        self._ensure()
        assert self.schema is not None
        safe_query = self.validate_sparql(query, limit)
        result = self.schema.query(safe_query)
        if result.type == "ASK":
            return [{"s": "ask", "p": "result", "o": str(result.askAnswer).lower()}]
        rows: list[dict[str, str]] = []
        for row in result:
            values = list(row)
            rows.append({
                "s": _shorten(values[0]) if len(values) > 0 and values[0] is not None else "",
                "p": _shorten(values[1]) if len(values) > 1 and values[1] is not None else "",
                "o": _shorten(values[2]) if len(values) > 2 and values[2] is not None else "",
            })
        return rows


@lru_cache(maxsize=1)
def get_ontology_service() -> OntologyService:
    return OntologyService()


def reset_ontology_service() -> None:
    """测试用：清空单例。"""
    get_ontology_service.cache_clear()
