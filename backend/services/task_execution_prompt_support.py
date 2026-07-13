from __future__ import annotations

from backend.shared import first_non_blank, string_value

CHARACTER_SHEET_REQUIREMENTS = (
    "生成类型：角色三视图设定图。",
    "必须输出同一角色的正面、侧面、背面三视图，放在同一张图中。",
    "三个视图都必须是完整从头到脚全身像，人物整体缩小并居中，头顶、双手、鞋子、脚底四周保留清晰留白，不得裁切或超出图片外。",
    "禁止半身像、胸像、近景特写、肖像照或过度放大构图；三个视图横向等距排列在同一张画布内。",
    "使用标准中性站姿，身体直立，双臂自然下垂或微微离身，双手空置，不做动作戏、剧情动作、表演动作或复杂姿势。",
    "只保留稳定穿戴配饰；禁止手拿、背负、牵引、互动或携带任何道具、武器、包袋、手机、文件、杯子、伞、花束等物体。",
    "脸、发型、服装、体型、年龄感和配饰保持一致。",
    "背景使用纯净浅色或纯白背景，不出现文字、箭头、水印、logo、说明标签或复杂场景。",
)

ASPECT_RATIO_4K_RESOLUTIONS = {
    "16:9": "3840x2160",
    "9:16": "2160x3840",
    "9:20": "1728x3840",
    "1:1": "2880x2880",
    "21:9": "3808x1632",
    "3:2": "3504x2336",
    "2:3": "2336x3504",
    "4:3": "3264x2448",
    "3:4": "2448x3264",
}


def build_character_sheet_prompt(name: str, description: str) -> str:
    parts = [
        f"角色名称：{first_non_blank(name, '未命名角色')}",
        f"角色设定：{description}",
        *CHARACTER_SHEET_REQUIREMENTS,
    ]
    return "\n".join(part for part in parts if part.strip())


def build_workspace_image_prompt(asset_type: str, title: str, description: str, has_references: bool) -> str:
    normalized_asset_type = string_value(asset_type)
    normalized_description = string_value(description)
    if normalized_asset_type in ("free", ""):
        return normalized_description
    parts = [
        f"素材标题：{first_non_blank(title, '工作台图片生成')}",
        f"素材描述：{normalized_description}",
    ]
    if has_references:
        parts.append("参考图要求：严格沿用参考图中的主体结构、外观锚点、材质和关键比例，不要重新设计核心主体。")
    if normalized_asset_type == "character_sheet":
        parts.extend(CHARACTER_SHEET_REQUIREMENTS)
    return "\n".join(parts)


def append_aspect_ratio_instruction(prompt: str, aspect_ratio: str) -> str:
    normalized_ratio = string_value(aspect_ratio)
    if not normalized_ratio or normalized_ratio.lower() in {"auto", "智能"}:
        return prompt
    resolution = ASPECT_RATIO_4K_RESOLUTIONS.get(normalized_ratio)
    resolution_text = f"（{resolution}）" if resolution else ""
    return (
        f"{prompt}\n画面比例：{normalized_ratio}。请使用该比例对应的 4K 分辨率{resolution_text}生成图片，"
        "按该画幅构图，不要自行拉伸或变形主体。"
    )


def build_video_clip_execution_prompt(prompt: str, max_length: int = 2200) -> str:
    if not prompt:
        return ""
    normalized = prompt.replace("\n", " ").strip()
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length] + "..."
