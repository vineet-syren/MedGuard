<template>
  <div class="marquee" aria-hidden="true">
    <span>{{ text }} · {{ text }} · </span>
    <span>{{ text }} · {{ text }} · </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text: string }>()
</script>

