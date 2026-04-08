import type { AgentDefinition, AgentId } from "@/types";

export const DEFAULT_AGENT_ID: AgentId = "ai-drama";

export const AGENT_DEFINITIONS: AgentDefinition[] = [
  {
    id: "ai-drama",
    name: "AI 剧总控 Agent",
    subtitle: "Script / Consistency / Stitch",
    description: "输入正文后一键拉起多 Agent 协同，自动决定风格、镜头节奏、拼接和音频规划。",
    accent: "#ff4d4f",
    accentSoft: "rgba(255, 77, 79, 0.16)",
    icon: "00",
    route: "/studio?agent=ai-drama",
    deliveryLabel: "Final Cut",
    capabilities: ["一键成片", "角色一致性", "镜头视频", "拼接总控"],
    defaultPrompt: "把正文交给多 Agent 自动拆成风格统一的分镜、镜头视频和最终 AI 剧成片。",
  },
  {
    id: "drama-editor",
    name: "短剧剪辑 Agent",
    subtitle: "Storyboard / Cut / Finish",
    description: "输入素材、节奏和投放目标，自动组织成短剧剪辑任务。",
    accent: "#ff5f57",
    accentSoft: "rgba(255, 95, 87, 0.16)",
    icon: "01",
    route: "/studio?agent=drama-editor",
    deliveryLabel: "Task",
    capabilities: ["素材接入", "创意提示词", "任务创建", "进度追踪"],
    defaultPrompt: "围绕冲突升级、镜头切点和情绪节奏输出短剧剪辑任务。",
  },
  {
    id: "visual-lab",
    name: "文生图 / 视频 Agent",
    subtitle: "Prompt / Render / Preview",
    description: "同一套界面同时负责图像和视频，重点是提示词与输出预览。",
    accent: "#9d7cff",
    accentSoft: "rgba(157, 124, 255, 0.16)",
    icon: "02",
    route: "/studio?agent=visual-lab",
    deliveryLabel: "Media",
    capabilities: ["图像生成", "视频生成", "结果预览"],
    defaultPrompt: "创建一段具备稳定构图、清晰主体和强氛围感的视觉生成请求。",
  },
  {
    id: "script-director",
    name: "文生脚本 Agent",
    subtitle: "Narrative / Tables / Prompt",
    description: "把故事片段转为可投喂生产的角色档案与分镜脚本。",
    accent: "#2dd4bf",
    accentSoft: "rgba(45, 212, 191, 0.16)",
    icon: "03",
    route: "/studio?agent=script-director",
    deliveryLabel: "Script",
    capabilities: ["角色档案", "分镜表格", "Markdown 输出", "一键复制"],
    defaultPrompt: "把故事正文输出成结构化的短剧脚本。",
  },
];

export function getAgentDefinition(agentId: AgentId): AgentDefinition {
  return AGENT_DEFINITIONS.find((agent) => agent.id === agentId) ?? AGENT_DEFINITIONS[0];
}

export function isAgentId(value: unknown): value is AgentId {
  return typeof value === "string" && AGENT_DEFINITIONS.some((agent) => agent.id === value);
}
