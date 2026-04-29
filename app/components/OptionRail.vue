<template>
  <section class="band">
    <div class="option-rail">
      <article v-for="(item, index) in items" :key="item.title" class="option-card" :class="{ dark: index % 2 === 0 }">
        <div class="big-num">{{ item.number }}</div>
        <div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.copy }}</p>
        </div>
        <NuxtLink v-if="item.to" class="btn" :class="{ inverse: index % 2 === 0 }" :to="item.to">Open</NuxtLink>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  items: Array<{ number: string; title: string; copy: string; to?: string }>
}>()
</script>
