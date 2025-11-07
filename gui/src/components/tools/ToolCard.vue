<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  badge: {
    type: String,
    default: ''
  },
  tone: {
    type: String,
    default: 'blue'
  }
})
</script>

<template>
  <article class="tool-card" :class="[`tone-${tone}`]">
    <header class="tool-card__header">
      <div>
        <p class="tool-card__subtitle">
          {{ subtitle }}
          <el-tag v-if="badge" size="small" type="info" effect="plain">{{ badge }}</el-tag>
        </p>
        <h2>{{ title }}</h2>
      </div>
      <div class="tool-card__actions">
        <slot name="actions" />
      </div>
    </header>
    <section class="tool-card__body">
      <slot />
    </section>
    <footer v-if="$slots.footer" class="tool-card__footer">
      <slot name="footer" />
    </footer>
  </article>
</template>
