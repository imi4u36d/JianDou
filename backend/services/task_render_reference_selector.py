"""Reference-image selection for task keyframe rendering."""

from __future__ import annotations

import re
from typing import Any

from backend.domain.task_record import TaskRecord
from backend.shared import first_non_blank, map_value, safe_int, string_value

MAX_CHARACTER_REFERENCE_IMAGES = 3
MAX_CHARACTER_REFERENCE_IMAGES_WITH_SCENE = 2


def frame_reference_image_urls(
    prompt: str,
    scene_reference_url: str,
    character_sheet_urls: list[str],
    character_definitions: list[Any],
) -> list[str]:
    references: list[str] = []
    normalized_scene_reference_url = string_value(scene_reference_url)
    if normalized_scene_reference_url:
        references.append(normalized_scene_reference_url)
    if not character_sheet_urls:
        return references

    max_character_references = (
        MAX_CHARACTER_REFERENCE_IMAGES_WITH_SCENE
        if normalized_scene_reference_url
        else MAX_CHARACTER_REFERENCE_IMAGES
    )
    selected_indexes = matching_character_indexes(prompt, character_definitions, len(character_sheet_urls))
    if not selected_indexes:
        selected_indexes = list(range(1, len(character_sheet_urls) + 1))
    for index in selected_indexes:
        if len(references) >= max_character_references + (1 if normalized_scene_reference_url else 0):
            break
        if index < 1 or index > len(character_sheet_urls):
            continue
        url = string_value(character_sheet_urls[index - 1])
        if url and url not in references:
            references.append(url)
    return references


def matching_character_indexes(
    prompt: str,
    character_definitions: list[Any],
    sheet_count: int,
) -> list[int]:
    normalized_prompt = string_value(prompt)
    if not normalized_prompt:
        return []
    lowered_prompt = normalized_prompt.lower()
    matches: list[tuple[int, int]] = []
    for index, character in enumerate(character_definitions[:sheet_count], start=1):
        name = string_value(getattr(character, "name", ""))
        if not name:
            continue
        position = character_name_position(normalized_prompt, lowered_prompt, name)
        if position >= 0:
            matches.append((position, index))
    matches.sort(key=lambda item: item[0])
    return [index for _, index in matches]


def character_name_position(prompt: str, lowered_prompt: str, name: str) -> int:
    normalized_name = string_value(name)
    if not normalized_name:
        return -1
    direct_position = prompt.find(normalized_name)
    if direct_position >= 0:
        return direct_position
    lowered_name = normalized_name.lower()
    if re.search(r"[A-Za-z0-9_]", lowered_name):
        match = re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(lowered_name)}(?![A-Za-z0-9_])",
            lowered_prompt,
        )
        return match.start() if match else -1
    return -1


def existing_character_sheet_urls(task: TaskRecord) -> dict[int, str]:
    resolved: dict[int, str] = {}
    for material in task.materials:
        if string_value(material.get("kind", material.get("assetRole", ""))) != "character_sheet":
            continue
        metadata = map_value(material.get("metadata"))
        index = safe_int(metadata.get("characterIndex"), 0)
        if index <= 0:
            clip_index = safe_int(material.get("clipIndex"), 0)
            index = clip_index - 1000 if clip_index > 1000 else 0
        url = first_non_blank(
            string_value(material.get("fileUrl")),
            string_value(material.get("previewUrl")),
            string_value(material.get("remoteUrl")),
        )
        if index > 0 and url.startswith("/storage/"):
            resolved[index] = url
    return resolved
