<template>
  <svg class="icon-glyph" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <g v-if="name === 'logo'">
      <path d="M12 3.8 18.8 6v5.2c0 4.3-2.7 7.1-6.8 8.9-4.1-1.8-6.8-4.6-6.8-8.9V6z" />
      <path d="M9 12.1 11.1 14l4-4.6" />
      <path d="M12 6.8v10" />
    </g>
    <g v-else-if="name === 'home'">
      <path d="M4 11.4 12 5l8 6.4" />
      <path d="M6.5 10.5v8h11v-8" />
      <path d="M10 18.5v-5h4v5" />
    </g>
    <g v-else-if="name === 'workbench'">
      <rect x="4" y="5" width="16" height="14" rx="3" />
      <path d="M4 10h16" />
      <path d="M8 14h4" />
      <path d="M15 14h1.8" />
    </g>
    <g v-else-if="name === 'panel-left'">
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M9 4v16" />
      <path d="m14 10-2 2 2 2" />
    </g>
    <g v-else-if="name === 'panel-right'">
      <rect x="4" y="4" width="16" height="16" rx="3" />
      <path d="M9 4v16" />
      <path d="m12 10 2 2-2 2" />
    </g>
    <g v-else-if="name === 'eye'">
      <path d="M3.5 12s3.1-5 8.5-5 8.5 5 8.5 5-3.1 5-8.5 5-8.5-5-8.5-5Z" />
      <circle cx="12" cy="12" r="2.5" />
    </g>
    <g v-else-if="name === 'eye-off'">
      <path d="m4 4 16 16" />
      <path d="M9.8 6.4A9 9 0 0 1 12 6c5.4 0 8.5 6 8.5 6a14.4 14.4 0 0 1-2.6 3.1" />
      <path d="M14.1 14.1A2.8 2.8 0 0 1 9.9 9.9" />
      <path d="M6.7 8.2A14 14 0 0 0 3.5 12s3.1 6 8.5 6a8.8 8.8 0 0 0 3.3-.6" />
    </g>
    <g v-else-if="name === 'maximize'">
      <path d="M8 4H4v4" />
      <path d="M16 4h4v4" />
      <path d="M8 20H4v-4" />
      <path d="M16 20h4v-4" />
    </g>
    <g v-else-if="name === 'minimize'">
      <path d="M4 8h4V4" />
      <path d="M20 8h-4V4" />
      <path d="M4 16h4v4" />
      <path d="M20 16h-4v4" />
    </g>
    <g v-else-if="name === 'key'">
      <circle cx="8" cy="14" r="3.5" />
      <path d="M11 12.5 20 3.5" />
      <path d="m15 8 2 2" />
      <path d="m17 6 2 2" />
    </g>
    <g v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a7.6 7.6 0 0 0-1.7-1L14.5 3h-5l-.3 3a7.6 7.6 0 0 0-1.7 1L5.1 6l-2 3.5L5 11a7 7 0 0 0 0 2l-1.9 1.5 2 3.5 2.4-1a7.6 7.6 0 0 0 1.7 1l.3 3h5l.3-3a7.6 7.6 0 0 0 1.7-1l2.4 1 2-3.5-2-1.5c.1-.3.1-.7.1-1Z" />
    </g>
    <g v-else-if="name === 'logout'">
      <path d="M10 5H6.5A2.5 2.5 0 0 0 4 7.5v9A2.5 2.5 0 0 0 6.5 19H10" />
      <path d="M14 8l4 4-4 4" />
      <path d="M18 12H9" />
    </g>
    <g v-else-if="name === 'integration'">
      <circle cx="6" cy="7" r="2.5" />
      <circle cx="18" cy="7" r="2.5" />
      <circle cx="12" cy="17" r="2.5" />
      <path d="m8.2 8.4 2.6 5.6" />
      <path d="m15.8 8.4-2.6 5.6" />
      <path d="M8.5 7h7" />
    </g>
    <g v-else-if="name === 'users'">
      <circle cx="9" cy="8" r="3" />
      <path d="M4.5 19c.6-3.2 2.2-4.8 4.5-4.8s3.9 1.6 4.5 4.8" />
      <path d="M15.5 10.5a2.6 2.6 0 1 0-.2-5.1" />
      <path d="M16 14.4c1.9.4 3.1 1.9 3.5 4.6" />
    </g>
    <g v-else-if="name === 'claims'">
      <path d="M7 4.5h7l3 3v12H7z" />
      <path d="M14 4.5v4h4" />
      <path d="M9.5 12h5" />
      <path d="M9.5 15h4" />
      <path d="m9.5 8.5 1.2 1.2 2.3-2.4" />
    </g>
    <g v-else-if="name === 'compliance'">
      <path d="M12 4.5 18.5 7v5.2c0 4-2.5 6.4-6.5 7.8-4-1.4-6.5-3.8-6.5-7.8V7z" />
      <path d="m8.7 12.4 2.2 2.2 4.5-5" />
    </g>
    <g v-else-if="name === 'ai'">
      <rect x="6" y="6" width="12" height="12" rx="3" />
      <path d="M9 3v3" />
      <path d="M15 3v3" />
      <path d="M9 18v3" />
      <path d="M15 18v3" />
      <path d="M3 9h3" />
      <path d="M18 9h3" />
      <path d="M3 15h3" />
      <path d="M18 15h3" />
      <path d="M10 12h4" />
    </g>
    <g v-else-if="name === 'workflow'">
      <rect x="4" y="5" width="5" height="5" rx="1.5" />
      <rect x="15" y="5" width="5" height="5" rx="1.5" />
      <rect x="9.5" y="14" width="5" height="5" rx="1.5" />
      <path d="M9 7.5h6" />
      <path d="M12 10v4" />
    </g>
    <g v-else-if="name === 'strategy'">
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="12" cy="12" r="3.5" />
      <path d="M12 4.5V2.8" />
      <path d="M19.5 12h1.7" />
      <path d="M12 19.5v1.7" />
      <path d="M4.5 12H2.8" />
    </g>
    <g v-else-if="name === 'ops'">
      <path d="M12 3.8v4" />
      <path d="M12 16.2v4" />
      <path d="M3.8 12h4" />
      <path d="M16.2 12h4" />
      <circle cx="12" cy="12" r="4.3" />
      <path d="m15.1 8.9 2-2" />
      <path d="m6.9 17.1 2-2" />
      <path d="m8.9 8.9-2-2" />
      <path d="m17.1 17.1-2-2" />
    </g>
    <g v-else-if="name === 'email'">
      <rect x="4" y="6" width="16" height="12" rx="3" />
      <path d="m5.5 8.5 6.5 5 6.5-5" />
    </g>
    <g v-else-if="name === 'content'">
      <rect x="4.5" y="5" width="15" height="14" rx="3" />
      <path d="M8 9h8" />
      <path d="M8 12h5" />
      <path d="M8 15h7" />
    </g>
    <g v-else-if="name === 'asset'">
      <path d="M4.5 8.5 12 4l7.5 4.5v7L12 20l-7.5-4.5z" />
      <path d="M4.8 8.8 12 13l7.2-4.2" />
      <path d="M12 13v7" />
    </g>
    <g v-else-if="name === 'evidence'">
      <path d="M5 5.5h9.5a4.5 4.5 0 0 1 0 9H12l-4 4v-4H5z" />
      <path d="M8 9h7" />
      <path d="M8 12h4" />
    </g>
    <g v-else-if="name === 'localization'">
      <circle cx="12" cy="12" r="8" />
      <path d="M4 12h16" />
      <path d="M12 4c2.2 2.2 3.2 4.8 3.2 8S14.2 17.8 12 20" />
      <path d="M12 4c-2.2 2.2-3.2 4.8-3.2 8s1 5.8 3.2 8" />
    </g>
    <g v-else-if="name === 'analytics'">
      <path d="M5 19V5" />
      <path d="M5 19h15" />
      <path d="M8 15l3-3 3 2 4-6" />
      <path d="M18 8h-3" />
    </g>
    <g v-else-if="name === 'visual'">
      <rect x="4" y="5" width="16" height="14" rx="3" />
      <circle cx="9" cy="10" r="1.5" />
      <path d="m7 17 4.2-4.2 2.6 2.6 2.2-2.2 2.5 3.8" />
    </g>
    <g v-else-if="name === 'pharma'">
      <path d="M9.4 4.6a4 4 0 0 1 5.7 5.7l-4.8 4.8a4 4 0 0 1-5.7-5.7z" />
      <path d="m8 6 6 6" />
      <path d="M14.5 14.5h5" />
      <path d="M17 12v5" />
    </g>
    <g v-else-if="name === 'vaccines'">
      <path d="m15 4 5 5" />
      <path d="m13 6 5 5-7.5 7.5a3.5 3.5 0 0 1-5-5z" />
      <path d="m8.4 14.8 3 3" />
      <path d="m11.4 11.8 3 3" />
    </g>
    <g v-else-if="name === 'diagnostics'">
      <circle cx="10" cy="10" r="5" />
      <path d="m14 14 5 5" />
      <path d="M8 10h4" />
      <path d="M10 8v4" />
    </g>
    <g v-else-if="name === 'medtech'">
      <rect x="5" y="6" width="14" height="12" rx="3" />
      <path d="M9 12h6" />
      <path d="M12 9v6" />
      <path d="M8 3.8v2.2" />
      <path d="M16 3.8v2.2" />
    </g>
    <g v-else-if="name === 'affiliate'">
      <circle cx="12" cy="8" r="3" />
      <path d="M5 20c.8-4.2 3.1-6.2 7-6.2s6.2 2 7 6.2" />
      <path d="M18.5 5.5 21 3" />
      <path d="M5.5 5.5 3 3" />
    </g>
    <g v-else-if="name === 'pricing'">
      <path d="M5 6h14v12H5z" />
      <path d="M8 10h8" />
      <path d="M8 14h4" />
      <path d="M16 14h.1" />
    </g>
    <g v-else>
      <circle cx="12" cy="12" r="8" />
      <path d="M8.5 12h7" />
      <path d="M12 8.5v7" />
    </g>
  </svg>
</template>

<script setup lang="ts">
defineProps<{
  name: string
}>()
</script>
