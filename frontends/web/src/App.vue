<template>
  <GlassBackground />
  <RouterView />
  <CreditDetailsDialog v-model="creditDialog.open" :initial-summary="creditDialog.initialSummary" />
  <AuthDialog />
  <MessageContainer />
</template>

<script setup lang="ts">
import AuthDialog from "@/components/auth/AuthDialog.vue";
import CreditDetailsDialog from "@/components/CreditDetailsDialog.vue";
import MessageContainer from "@/components/common/MessageContainer.vue";
import GlassBackground from "@/components/layout/GlassBackground.vue";
import { useCreditDialogState } from "@/composables/useCreditDialog";

const creditDialog = useCreditDialogState();
</script>
