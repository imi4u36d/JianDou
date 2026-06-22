<template>
  <GlassBackground />
  <RouterView />
  <AuthDialog />
  <MessageContainer />
</template>

<script setup lang="ts">
import AuthDialog from "@/components/auth/AuthDialog.vue";
import MessageContainer from "@/components/common/MessageContainer.vue";
import GlassBackground from "@/components/layout/GlassBackground.vue";
</script>
