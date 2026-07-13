"""Character definition extraction from storyboard markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_LIST_PATTERN = re.compile(r"^[-*]\s*(?P<name>[^：:|]+)[:：]\s*(?P<definition>.+)$")
_APPEARANCE_PATTERN = re.compile(
    r"外观锚点[:：](?P<appearance>.*?)(?:[；;。.]\s*(?:人物定位|行为特征|说话风格)[:：]|$)"
)
_UNKNOWN_VALUES = {"未明确", "不明确", "未知", "无", "无明确"}


@dataclass(frozen=True)
class CharacterDefinition:
    name: str = ""
    appearance: str = ""
    definition: str = ""

    def __post_init__(self) -> None:
        if not self.definition:
            object.__setattr__(self, "definition", self.appearance)


class _CharacterDefinitionBuilder:
    def __init__(self, name: str) -> None:
        self._name = name
        self._single_row_definition = ""
        self._single_row_appearance = ""
        self._gender = ""
        self._age = ""
        self._parts: dict[str, str] = {}

    @staticmethod
    def from_single_row(
        name: str,
        gender_age: str,
        position: str,
        face: str,
        hair: str,
        body: str,
        clothing: str,
        stable_accessories: str,
        immutable_visual: str,
        appearance: str,
        behavior: str,
        speech: str,
    ) -> _CharacterDefinitionBuilder:
        builder = _CharacterDefinitionBuilder(name)
        builder._single_row_appearance = _join_labeled_known_values(
            ("性别年龄", gender_age),
            ("脸部五官", face),
            ("发型", hair),
            ("体型身高", body),
            ("服装", clothing),
            ("稳定穿戴配饰", stable_accessories),
            ("不可变视觉锚点", _first_known_value(immutable_visual, appearance)),
        ) or _trim(appearance)
        chunks: list[str] = []
        for label, value in (
            ("性别年龄", gender_age),
            ("人物定位", position),
            ("脸部五官", face),
            ("发型", hair),
            ("体型身高", body),
            ("服装", clothing),
            ("稳定穿戴配饰", stable_accessories),
            ("不可变视觉锚点", immutable_visual),
            ("外观锚点", appearance),
            ("行为气质", behavior),
            ("说话风格", speech),
        ):
            _add_known_chunk(chunks, label, value)
        builder._single_row_definition = "；".join(chunks)
        return builder

    def add_detail(self, gender: str, age: str, part: str, detail: str) -> None:
        if not self._gender and gender:
            self._gender = gender
        if not self._age and age:
            self._age = age
        if part and detail:
            self._parts[part] = detail

    def build(self) -> CharacterDefinition:
        if self._single_row_appearance:
            return CharacterDefinition(self._name, self._single_row_appearance, self._single_row_definition)
        chunks = [label + value for label, value in (("性别：", self._gender), ("年龄：", self._age)) if value]
        chunks.extend(f"{part}：{detail}" for part, detail in self._parts.items())
        definition = "；".join(chunks)
        return CharacterDefinition(self._name, definition, definition)


@dataclass
class _CharacterTableSchema:
    header_cells: list[str] = field(default_factory=list)
    name_index: int | None = None
    gender_age_index: int | None = None
    position_index: int | None = None
    appearance_index: int | None = None
    face_index: int | None = None
    hair_index: int | None = None
    body_index: int | None = None
    clothing_index: int | None = None
    stable_accessories_index: int | None = None
    immutable_visual_index: int | None = None
    behavior_index: int | None = None
    speech_index: int | None = None
    gender_index: int | None = None
    age_index: int | None = None
    part_index: int | None = None
    detail_index: int | None = None

    @classmethod
    def from_header(cls, headers: list[str]) -> _CharacterTableSchema:
        return cls(
            header_cells=list(headers),
            name_index=_resolve_header(headers, "角色", "姓名", "名称"),
            gender_age_index=_resolve_header(headers, "性别年龄", "性别与年龄", "年龄性别"),
            position_index=_resolve_header(headers, "人物定位"),
            appearance_index=_resolve_header(headers, "外观锚点", "外观定义", "外形定义", "人物外观"),
            face_index=_resolve_header(headers, "脸部五官", "脸部", "五官", "面部特征"),
            hair_index=_resolve_header(headers, "发型"),
            body_index=_resolve_header(headers, "体型身高", "身高体型", "体型", "身高"),
            clothing_index=_resolve_header(headers, "服装", "着装", "衣着"),
            stable_accessories_index=_resolve_header(headers, "稳定穿戴配饰", "固定穿戴配饰", "稳定配饰", "穿戴配饰", "配饰"),
            immutable_visual_index=_resolve_header(headers, "不可变视觉锚点", "固定视觉锚点", "视觉锚点"),
            behavior_index=_resolve_header(headers, "行为气质", "行为特征", "气质"),
            speech_index=_resolve_header(headers, "说话风格"),
            gender_index=_resolve_header(headers, "性别"),
            age_index=_resolve_header(headers, "年龄"),
            part_index=_resolve_header(headers, "部位"),
            detail_index=_resolve_header(headers, "详细描述", "描述"),
        )

    @staticmethod
    def looks_like_header(cells: list[str]) -> bool:
        normalized = [_normalize_header(cell) for cell in cells]
        has_name = any(_contains_any(cell, "角色", "姓名", "名称") for cell in normalized)
        has_appearance = any(_contains_any(cell, "外观锚点", "外观定义", "外形定义") for cell in normalized)
        has_visual = any(_contains_any(cell, "脸部五官", "发型", "体型身高", "服装", "不可变视觉锚点") for cell in normalized)
        has_legacy = any("部位" in cell for cell in normalized) and any(_contains_any(cell, "详细描述", "描述") for cell in normalized)
        return has_name and (has_appearance or has_visual or has_legacy)

    def is_single_row(self) -> bool:
        return self.name_index is not None and self.position_index is not None and self.behavior_index is not None and self.speech_index is not None and any(
            index is not None for index in (self.appearance_index, self.face_index, self.hair_index, self.body_index, self.clothing_index, self.immutable_visual_index)
        )

    def is_valid(self) -> bool:
        return self.is_single_row() or all(index is not None for index in (self.name_index, self.gender_index, self.age_index, self.part_index, self.detail_index))

    def is_header_row(self, cells: list[str]) -> bool:
        return len(cells) == len(self.header_cells) and all(
            _normalize_header(cell) == _normalize_header(self.header_cells[index]) for index, cell in enumerate(cells)
        )

    @staticmethod
    def value(cells: list[str], index: int | None) -> str:
        return cells[index] if index is not None and 0 <= index < len(cells) else ""


class StoryboardCharacterParser:
    def extract_character_definitions(self, storyboard_markdown: str) -> list[CharacterDefinition]:
        normalized = "" if storyboard_markdown is None else str(storyboard_markdown).strip()
        definitions_start = normalized.find("【角色定义信息】")
        if definitions_start < 0:
            return []
        script_start = normalized.find("【分镜脚本】")
        block = normalized[definitions_start:script_start] if script_start > definitions_start else normalized[definitions_start:]
        return self._from_list(block) or self._from_table(block)

    def _from_list(self, block: str) -> list[CharacterDefinition]:
        definitions: list[CharacterDefinition] = []
        for raw_line in block.splitlines():
            matcher = _LIST_PATTERN.match(raw_line.strip())
            if not matcher:
                continue
            name = _normalize(matcher.group("name"))
            definition = _normalize(matcher.group("definition"))
            if name and definition:
                definitions.append(CharacterDefinition(name, _appearance_anchor(definition), definition))
        return definitions

    def _from_table(self, block: str) -> list[CharacterDefinition]:
        builders: dict[str, _CharacterDefinitionBuilder] = {}
        schema = _CharacterTableSchema()
        for raw_line in block.splitlines():
            cells = _split_table_row(raw_line.strip())
            if not cells or _is_divider_row(cells):
                continue
            if _CharacterTableSchema.looks_like_header(cells):
                schema = _CharacterTableSchema.from_header(cells)
                continue
            if not schema.is_valid() or schema.is_header_row(cells):
                continue
            name = _normalize(schema.value(cells, schema.name_index))
            if schema.is_single_row():
                values = {
                    "gender_age": _normalize(schema.value(cells, schema.gender_age_index)),
                    "position": _normalize(schema.value(cells, schema.position_index)),
                    "face": _normalize(schema.value(cells, schema.face_index)),
                    "hair": _normalize(schema.value(cells, schema.hair_index)),
                    "body": _normalize(schema.value(cells, schema.body_index)),
                    "clothing": _normalize(schema.value(cells, schema.clothing_index)),
                    "stable_accessories": _normalize(schema.value(cells, schema.stable_accessories_index)),
                    "immutable_visual": _normalize(schema.value(cells, schema.immutable_visual_index)),
                    "appearance": _trim(schema.value(cells, schema.appearance_index)),
                    "behavior": _normalize(schema.value(cells, schema.behavior_index)),
                    "speech": _normalize(schema.value(cells, schema.speech_index)),
                }
                visual_values = tuple(values[key] for key in ("appearance", "gender_age", "face", "hair", "body", "clothing", "stable_accessories", "immutable_visual"))
                if name and any(_has_known(value) for value in visual_values):
                    builders.setdefault(name, _CharacterDefinitionBuilder.from_single_row(name, **values))
                continue
            gender = _normalize(schema.value(cells, schema.gender_index))
            age = _normalize(schema.value(cells, schema.age_index))
            part = _normalize(schema.value(cells, schema.part_index))
            detail = _normalize(schema.value(cells, schema.detail_index))
            if name and part and detail:
                builders.setdefault(name, _CharacterDefinitionBuilder(name)).add_detail(gender, age, part, detail)
        definitions = [builder.build() for builder in builders.values()]
        return [definition for definition in definitions if definition.name and definition.appearance]


def _normalize(value: object) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")).strip()


def _normalize_header(value: str) -> str:
    return re.sub(r"[\s_\-—–:：()（）【】\[\]]+", "", _normalize(value)).lower()


def _trim(value: object) -> str:
    return re.sub(r"[。；;，,]+$", "", _normalize(value)).strip()


def _has_known(value: str) -> bool:
    normalized = _trim(value)
    return bool(normalized) and normalized not in _UNKNOWN_VALUES


def _first_known_value(*values: str) -> str:
    return next((_trim(value) for value in values if _has_known(value)), "")


def _add_known_chunk(chunks: list[str], label: str, value: str) -> None:
    if _has_known(value):
        chunks.append(f"{label}：{_trim(value)}")


def _join_labeled_known_values(*pairs: tuple[str, str]) -> str:
    chunks: list[str] = []
    for label, value in pairs:
        _add_known_chunk(chunks, label, value)
    return "；".join(chunks)


def _resolve_header(headers: list[str], *aliases: str) -> int | None:
    return next((index for index, header in enumerate(headers) if any(_normalize_header(alias) in _normalize_header(header) for alias in aliases)), None)


def _contains_any(text: str, *values: str) -> bool:
    return any(value in text for value in values)


def _appearance_anchor(definition: str) -> str:
    matcher = _APPEARANCE_PATTERN.search(_normalize(definition))
    return _trim(matcher.group("appearance")) if matcher and _trim(matcher.group("appearance")) else _trim(definition)


def _split_table_row(row: str) -> list[str]:
    if not row.startswith("|"):
        return []
    content = row[1:-1] if row.endswith("|") else row[1:]
    return [part.strip() for part in content.split("|")]


def _is_divider_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell or "") is not None for cell in cells)
