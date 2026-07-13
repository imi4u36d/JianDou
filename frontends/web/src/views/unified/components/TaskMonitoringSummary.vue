<template>
  <div v-if="monitoringRows.length || artifactRows.length" class="task-monitoring-summary">
    <section v-if="monitoringRows.length" class="task-monitoring-card">
      <h3>监控</h3>
      <div class="task-monitoring-params">
        <div v-for="item in monitoringRows" :key="item.label" class="task-monitoring-params__row">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>

    <section v-if="artifactRows.length" class="task-monitoring-card">
      <div class="task-monitoring-card__head">
        <h3>产物</h3>
        <span class="surface-chip" :title="artifactDirectoryHint">{{ shortArtifactDirectoryHint }}</span>
      </div>
      <div class="task-monitoring-params">
        <div v-for="item in artifactRows" :key="item.label" class="task-monitoring-params__row">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
interface SummaryRow {
  label: string;
  value: string;
}

defineProps<{
  monitoringRows: SummaryRow[];
  artifactRows: SummaryRow[];
  artifactDirectoryHint: string;
  shortArtifactDirectoryHint: string;
}>();
</script>

<style scoped src="./task-monitoring-summary.css"></style>
