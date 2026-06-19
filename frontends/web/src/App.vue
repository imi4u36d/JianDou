<template>
  <RouterView />
  <AuthDialog />
  <MessageContainer />
</template>

<script setup lang="ts">
import AuthDialog from "@/components/auth/AuthDialog.vue";
import MessageContainer from "@/components/common/MessageContainer.vue";
</script>
