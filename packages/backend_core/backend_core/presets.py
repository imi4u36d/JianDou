from __future__ import annotations

from .schemas import TaskPreset


TASK_PRESETS: tuple[TaskPreset, ...] = (
    TaskPreset(
        key="douyin_hotcut",
        name="抖音爆款切条",
        description="适合强冲突、强反转的短剧高能片段，优先提升首刷停留。",
        defaultTitle="抖音爆款版",
        editingMode="drama",
        platform="douyin",
        aspectRatio="9:16",
        minDurationSeconds=15,
        maxDurationSeconds=30,
        outputCount=3,
        introTemplate="flash_hook",
        outroTemplate="suspense_hold",
        creativePrompt="优先保留冲突、反转和情绪爆点，开头直接打到高压场面，结尾停在最想追下去的一拍。",
    ),
    TaskPreset(
        key="feed_conversion",
        name="信息流转化版",
        description="适合广告投放和素材 A/B 测试，突出卖点和行动召唤。",
        defaultTitle="信息流投放版",
        editingMode="drama",
        platform="wechat",
        aspectRatio="9:16",
        minDurationSeconds=20,
        maxDurationSeconds=35,
        outputCount=4,
        introTemplate="pressure_build",
        outroTemplate="question_freeze",
        creativePrompt="保留人物关系推进和信息转折，结尾卡在一句反问或关键停顿，兼顾转化和追看欲望。",
    ),
    TaskPreset(
        key="episode_highlight",
        name="剧集高能版",
        description="适合长剧切条和连续集内容，突出剧情推进和高能转折。",
        defaultTitle="剧集高能版",
        editingMode="drama",
        platform="kuaishou",
        aspectRatio="9:16",
        minDurationSeconds=25,
        maxDurationSeconds=45,
        outputCount=3,
        introTemplate="cold_open",
        outroTemplate="follow_hook",
        creativePrompt="优先保留冲突升级、角色关系变化和关键反转，片尾要形成追更钩子，适合连续剧切条。",
    ),
    TaskPreset(
        key="longform_snippet",
        name="长视频精华版",
        description="适合横版内容截取精华段落，兼顾信息传达和观看完整性。",
        defaultTitle="长视频精华版",
        editingMode="drama",
        platform="xiaohongshu",
        aspectRatio="16:9",
        minDurationSeconds=30,
        maxDurationSeconds=60,
        outputCount=2,
        introTemplate="none",
        outroTemplate="question_freeze",
        creativePrompt="保留信息完整度和关键观点，剪辑更克制，但结尾仍需留下反问或未说尽的悬念。",
    ),
    TaskPreset(
        key="music_sync_mixcut",
        name="音乐卡点混剪",
        description="适合节奏感强的多素材混剪，优先对白闪快切、鼓点对齐和爆点推进。",
        defaultTitle="音乐卡点混剪版",
        editingMode="mixcut",
        platform="douyin",
        aspectRatio="9:16",
        minDurationSeconds=15,
        maxDurationSeconds=28,
        outputCount=4,
        introTemplate="flash_hook",
        outroTemplate="suspense_hold",
        creativePrompt="优先按鼓点和爆点组织多素材镜头，开头直接给最强节奏点，中段强化快切和反差，结尾停在最后一次强拍后的一瞬。",
        mixcutContentType="generic",
        mixcutStylePreset="music_sync",
    ),
    TaskPreset(
        key="drama_conflict_mixcut",
        name="剧情冲突混剪",
        description="适合多段剧情素材联合编排，强调人物对照、冲突递进和情绪收束。",
        defaultTitle="剧情冲突混剪版",
        editingMode="mixcut",
        platform="kuaishou",
        aspectRatio="9:16",
        minDurationSeconds=18,
        maxDurationSeconds=36,
        outputCount=3,
        introTemplate="cold_open",
        outroTemplate="follow_hook",
        creativePrompt="请把多段剧情素材组织成一条冲突递进明确的混剪，优先保留人物对峙、情绪升级和反转前夜，结尾留出追更钩子。",
        mixcutContentType="drama",
        mixcutStylePreset="director",
    ),
)


def get_task_presets() -> list[TaskPreset]:
    return [preset.model_copy(deep=True) for preset in TASK_PRESETS]


def get_task_preset(key: str) -> TaskPreset | None:
    for preset in TASK_PRESETS:
        if preset.key == key:
            return preset.model_copy(deep=True)
    return None
