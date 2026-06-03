<script setup>
defineProps({
  feature: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['open'])

const onClick = (feature) => {
  if (feature.disabled) return
  emit('open', feature.id)
}
</script>

<template>
  <div
    class="feature-card"
    :class="[`card-${feature.color}`, { disabled: feature.disabled }]"
    @click="onClick(feature)"
  >
    <!-- 卡片发光效果 -->
    <div class="card-glow"></div>

    <!-- 卡片内容 -->
    <div class="card-header">
      <div class="icon-wrapper">
        <el-icon class="feature-icon">
          <component :is="feature.icon" />
        </el-icon>
      </div>
      <div class="title-area">
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.desc }}</p>
      </div>
    </div>

    <ul class="feature-points">
      <li v-for="point in feature.points" :key="point">
        <span class="point-dot"></span>
        <span>{{ point }}</span>
      </li>
    </ul>

    <div class="card-footer">
      <div class="tag-list">
        <span v-for="tag in feature.tags" :key="tag" class="feature-tag">
          {{ tag }}
        </span>
      </div>
<!--              <button class="action-btn" :disabled="feature.disabled">-->
<!--                {{ feature.action }}-->
<!--                <span class="btn-arrow">→</span>-->
<!--              </button>-->
    </div>
  </div>
</template>

<style scoped>
/* ???? */
.feature-card {
  --card-accent: var(--ppx-neon-blue);
  --card-accent-soft: rgba(14, 165, 164, 0.35);
  position: relative;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.7));
  border: 1px solid var(--ppx-glass-border);
  border-radius: 20px;
  padding: 20px;
  cursor: pointer;
  transition: all var(--ppx-transition-normal);
  overflow: hidden;
  opacity: 0;
  transform: translateY(16px);
  animation: cardRise 0.6s ease forwards;
  animation-delay: var(--delay);
  clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 18px 100%, 0 calc(100% - 18px));
  box-shadow: var(--ppx-shadow-sm);
}

.feature-card::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  pointer-events: none;
  opacity: 0.6;
}

.feature-card:hover {
  transform: translateY(-6px) rotate(-0.2deg);
  border-color: rgba(44, 36, 29, 0.22);
  box-shadow: var(--ppx-shadow-md);
}

.feature-card.disabled {
  opacity: 0.45;
  pointer-events: none;
}

.card-cyan {
  --card-accent: var(--ppx-neon-blue);
}

.card-purple {
  --card-accent: var(--ppx-neon-purple);
  --card-accent-soft: rgba(249, 115, 22, 0.35);
}

.card-pink {
  --card-accent: var(--ppx-neon-pink);
  --card-accent-soft: rgba(245, 158, 11, 0.35);
}

.card-green {
  --card-accent: var(--ppx-neon-green);
  --card-accent-soft: rgba(132, 204, 22, 0.35);
}

.card-blue {
  --card-accent: var(--ppx-neon-cyan);
  --card-accent-soft: rgba(34, 193, 220, 0.35);
}

.card-orange {
  --card-accent: var(--ppx-neon-orange);
  --card-accent-soft: rgba(234, 88, 12, 0.35);
}

.card-red {
  --card-accent: #dc2626;
  --card-accent-soft: rgba(220, 38, 38, 0.35);
}

.card-indigo {
  --card-accent: #0f766e;
  --card-accent-soft: rgba(15, 118, 110, 0.35);
}

.card-gray {
  --card-accent: #64748b;
  --card-accent-soft: rgba(100, 116, 139, 0.35);
}

.card-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top left, var(--card-accent-soft) 0%, transparent 65%);
  opacity: 0.8;
  pointer-events: none;
}

.card-header {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
}

.feature-icon {
  width: 22px;
  height: 22px;
  font-size: 22px;
  line-height: 1;
  color: var(--card-accent);
  flex-shrink: 0;
}

.feature-icon :deep(svg) {
  display: block;
  width: 100%;
  height: 100%;
}

.title-area h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--ppx-text-primary);
}

.title-area p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--ppx-text-muted);
}

.feature-points {
  list-style: none;
  padding: 0;
  margin: 0 0 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: var(--ppx-text-secondary);
}

.feature-points li {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.point-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
  background: var(--card-accent);
  box-shadow: 0 0 0 3px var(--card-accent-soft);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
}

.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.feature-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 9px;
  background: rgba(44, 36, 29, 0.06);
  border: 1px solid rgba(44, 36, 29, 0.12);
  border-radius: 999px;
  color: var(--ppx-text-muted);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ppx-text-primary);
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(44, 36, 29, 0.18);
  border-radius: 10px;
  cursor: pointer;
  transition: all var(--ppx-transition-fast);
  flex-shrink: 0;
}

.action-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.95);
  border-color: var(--card-accent);
  color: var(--card-accent);
  transform: translateX(2px);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-arrow {
  transition: transform 0.2s;
}

.action-btn:hover:not(:disabled) .btn-arrow {
  transform: translateX(3px);
}

@keyframes cardRise {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
