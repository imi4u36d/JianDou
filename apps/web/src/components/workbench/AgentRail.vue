<template>
  <aside class="agent-rail" :class="collapsed ? 'agent-rail-collapsed' : ''">
    <div class="agent-rail-head">
      <div class="agent-rail-brand">
        <span class="agent-rail-mark"></span>
        <div v-if="!collapsed" class="agent-rail-brand-copy">
          <strong>AI Cut Studio</strong>
          <span>Agent Workspace</span>
        </div>
      </div>

      <button type="button" class="agent-rail-toggle" @click="$emit('toggle')">
        {{ collapsed ? "展开" : "收起" }}
      </button>
    </div>

    <nav class="agent-rail-list" aria-label="Agent 菜单">
      <button
        v-for="agent in agents"
        :key="agent.id"
        type="button"
        class="agent-rail-item"
        :class="agent.id === selectedAgentId ? 'agent-rail-item-active' : ''"
        :style="{ '--agent-accent': agent.accent }"
        @click="$emit('select', agent.id)"
      >
        <span class="agent-rail-item-accent"></span>
        <span class="agent-rail-item-icon">{{ agent.icon }}</span>
        <span v-if="!collapsed" class="agent-rail-item-copy">
          <span class="agent-rail-item-title-row">
            <strong>{{ agent.name }}</strong>
            <span class="agent-rail-item-status">{{ statusByAgent[agent.id] || "idle" }}</span>
          </span>
          <span class="agent-rail-item-subtitle">{{ agent.subtitle }}</span>
          <span class="agent-rail-item-description">{{ agent.description }}</span>
        </span>
      </button>
    </nav>

    <div v-if="!collapsed" class="agent-rail-footer">
      <p>四位 Agent 共享一套视觉语言和任务历史。</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { AgentDefinition, AgentId } from "@/types";

defineProps<{
  agents: AgentDefinition[];
  selectedAgentId: AgentId;
  statusByAgent: Record<string, string>;
  collapsed: boolean;
}>();

defineEmits<{
  select: [agentId: AgentId];
  toggle: [];
}>();
</script>

<style scoped>
.agent-rail {
  position: sticky;
  top: 1rem;
  display: grid;
  gap: 1rem;
  align-content: start;
  border: 1px solid #e8e2d8;
  border-radius: 1.6rem;
  background:
    radial-gradient(circle at top right, rgba(37, 99, 235, 0.06), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 245, 239, 0.96));
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
  padding: 1rem;
  transition:
    width 180ms ease,
    transform 180ms ease,
    box-shadow 180ms ease;
}

.agent-rail-collapsed {
  padding-inline: 0.75rem;
}

.agent-rail-head,
.agent-rail-brand,
.agent-rail-item-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.agent-rail-brand {
  min-width: 0;
}

.agent-rail-mark {
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #14b8a6);
  box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.08);
  flex-shrink: 0;
}

.agent-rail-brand-copy {
  display: grid;
  gap: 0.08rem;
}

.agent-rail-brand-copy strong {
  color: #24303f;
  font-size: 0.96rem;
}

.agent-rail-brand-copy span {
  color: #7b8594;
  font-size: 0.72rem;
}

.agent-rail-toggle {
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #fff;
  padding: 0.42rem 0.7rem;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 700;
  transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
}

.agent-rail-toggle:hover {
  transform: translateY(-1px);
  border-color: #c7d2fe;
  box-shadow: 0 10px 18px rgba(37, 99, 235, 0.08);
}

.agent-rail-list {
  display: grid;
  gap: 0.7rem;
}

.agent-rail-item {
  display: grid;
  grid-template-columns: 0.4rem 2.5rem minmax(0, 1fr);
  gap: 0.8rem;
  align-items: start;
  border: 1px solid #e8e2d8;
  border-radius: 1.2rem;
  background: rgba(255, 255, 255, 0.92);
  padding: 0.85rem;
  text-align: left;
  color: #24303f;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.agent-rail-item:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--agent-accent) 26%, #e8e2d8);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
}

.agent-rail-item-active {
  border-color: color-mix(in srgb, var(--agent-accent) 42%, #dbe3ef);
  box-shadow: 0 18px 44px rgba(37, 99, 235, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 1), rgba(248, 250, 255, 0.98));
}

.agent-rail-item-accent {
  width: 0.4rem;
  height: 100%;
  min-height: 2.5rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--agent-accent) 70%, #94a3b8);
}

.agent-rail-item-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.95rem;
  background: color-mix(in srgb, var(--agent-accent) 10%, #f8fafc);
  color: color-mix(in srgb, var(--agent-accent) 82%, #1e293b);
  font-size: 0.82rem;
  font-weight: 800;
}

.agent-rail-item-copy {
  display: grid;
  gap: 0.3rem;
  min-width: 0;
}

.agent-rail-item-title-row strong {
  color: #24303f;
  font-size: 0.96rem;
}

.agent-rail-item-status {
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--agent-accent) 24%, #dbe2ec);
  background: color-mix(in srgb, var(--agent-accent) 10%, #f8fafc);
  padding: 0.18rem 0.45rem;
  color: #405164;
  font-size: 0.68rem;
  text-transform: uppercase;
}

.agent-rail-item-subtitle {
  color: #6b7280;
  font-size: 0.75rem;
}

.agent-rail-item-description {
  color: #88919f;
  line-height: 1.55;
  font-size: 0.72rem;
}

.agent-rail-footer {
  border-top: 1px solid #ece7de;
  padding-top: 0.1rem;
  color: #7b8594;
  font-size: 0.78rem;
  line-height: 1.65;
}

@media (max-width: 1100px) {
  .agent-rail {
    position: relative;
    top: 0;
  }
}

@media (max-width: 720px) {
  .agent-rail-item {
    grid-template-columns: 0.4rem 2.2rem minmax(0, 1fr);
  }
}
</style>
