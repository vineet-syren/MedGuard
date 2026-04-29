<template>
  <div class="mock-screen">
    <div class="mock-top">
      <span>{{ title }}</span>
      <span>{{ index }}</span>
    </div>
    <div class="mock-grid">
      <div class="mock-block light">
        <strong>{{ primary }}</strong><br>
        {{ primaryDetail }}
      </div>
      <div class="mock-block">
        {{ metricLabel }}<br>
        <strong>{{ metric }}</strong>
      </div>
    </div>
    <div class="mock-block">{{ detail }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  index: string
  primary: string
  primaryDetail: string
  metricLabel: string
  metric: string
  detail: string
}>()
</script>

