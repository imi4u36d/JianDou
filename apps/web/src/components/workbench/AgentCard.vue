<template>
  <button
    class="agent-card"
    :class="active ? 'agent-card-active' : ''"
    :style="{ '--agent-accent': agent.accent }"
    type="button"
    @click="$emit('select', agent.id)"
  >
    <div class="agent-card-top">
      <div>
        <p class="agent-card-kicker">{{ agent.deliveryLabel }}</p>
        <h3 class="agent-card-title">{{ agent.name }}</h3>
      </div>
      <span class="agent-card-index" :style="{ '--agent-accent': agent.accent }">{{ agent.icon }}</span>
    </div>

    <p class="agent-card-subtitle">{{ agent.subtitle }}</p>
    <p class="agent-card-description">{{ agent.description }}</p>

    <div class="agent-card-pills">
      <span v-for="capability in agent.capabilities.slice(0, 3)" :key="capability" class="agent-pill">
        {{ capability }}
      </span>
    </div>

    <div class="agent-card-footer">
      <span class="agent-state" :style="{ '--agent-accent': agent.accent }">{{ statusLabel }}</span>
      <span class="agent-card-link">打开 Agent</span>
    </div>
  </button>
</template>

<script setup lang="ts">
import type { AgentDefinition } from "@/types";

defineProps<{
  agent: AgentDefinition;
  active?: boolean;
  statusLabel: string;
}>();

defineEmits<{
  select: [agentId: string];
}>();
</script>

<style scoped>
.agent-card {
  display: grid;
  gap: 0.85rem;
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--agent-accent) 18%, transparent), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.02));
  cursor: pointer;
  padding: 1rem;
  text-align: left;
  color: #f5f5f5;
  box-shadow: 0 18px 56px rgba(0, 0, 0, 0.28);
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease;
}

.agent-card:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--agent-accent) 38%, rgba(255, 255, 255, 0.08));
  box-shadow: 0 22px 64px rgba(0, 0, 0, 0.34);
}

.agent-card-active {
  border-color: color-mix(in srgb, var(--agent-accent) 52%, rgba(255, 255, 255, 0.08));
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--agent-accent) 22%, transparent), transparent 26%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.03));
  box-shadow:
    0 24px 72px rgba(0, 0, 0, 0.38),
    0 0 0 1px color-mix(in srgb, var(--agent-accent) 18%, transparent);
}

.agent-card-top,
.agent-card-footer {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.agent-card-kicker {
  margin: 0;
  color: rgba(255, 255, 255, 0.42);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.agent-card-title {
  margin: 0.36rem 0 0;
  font-size: 1.08rem;
  font-weight: 700;
  color: #fafafa;
}

.agent-card-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 9999px;
  border: 1px solid color-mix(in srgb, var(--agent-accent) 30%, rgba(255, 255, 255, 0.1));
  background: color-mix(in srgb, var(--agent-accent) 18%, rgba(255, 255, 255, 0.03));
  color: #fff;
  font-size: 0.72rem;
  font-weight: 800;
}

.agent-card-subtitle {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.84rem;
}

.agent-card-description {
  margin: 0;
  color: rgba(255, 255, 255, 0.52);
  line-height: 1.75;
  font-size: 0.82rem;
}

.agent-card-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.agent-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  padding: 0.26rem 0.55rem;
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.68rem;
}

.agent-state {
  border-radius: 9999px;
  border: 1px solid color-mix(in srgb, var(--agent-accent) 30%, rgba(255, 255, 255, 0.08));
  background: color-mix(in srgb, var(--agent-accent) 14%, rgba(255, 255, 255, 0.03));
  padding: 0.25rem 0.52rem;
  color: #fff;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
}

.agent-card-link {
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
</style>
