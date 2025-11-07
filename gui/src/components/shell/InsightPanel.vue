<script setup>
import { computed, ref } from 'vue'
import dayjs from '@/utils/dayjs'
import { useToolkitStore } from '@/stores/toolkit'

const store = useToolkitStore()
const activeTab = ref('history')

const timeline = computed(() => store.activityTimeline)
const favorites = computed(() => store.favoriteClipboardItems.slice(0, 5))
const metrics = computed(() => store.metrics.latest)

const handleAutoSync = (val) => {
  store.cloudSync.auto = val
  store.persistPreferences()
}

const handleIntervalChange = (val) => {
  store.setMetricInterval(val)
}
</script>

<template>
  <aside class="insight-panel glass-panel">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="历史" name="history">
        <el-timeline>
          <el-timeline-item
            v-for="event in timeline"
            :key="event.id"
            :timestamp="dayjs(event.timestamp).format('HH:mm:ss')"
            placement="top"
            type="primary"
          >
            <p class="insight-panel__event-title">{{ event.title }}</p>
            <small>{{ event.detail }}</small>
          </el-timeline-item>
          <el-empty v-if="!timeline.length" description="暂无操作" />
        </el-timeline>
      </el-tab-pane>

      <el-tab-pane label="收藏" name="favorites">
        <div v-if="favorites.length" class="favorites-list">
          <article
            v-for="fav in favorites"
            :key="fav.id"
            class="favorite-card"
          >
            <header>
              <strong>{{ fav.summary }}</strong>
              <el-tag v-if="fav.type" size="small" type="info">{{ fav.type }}</el-tag>
            </header>
            <p>{{ fav.content.slice(0, 80) }}</p>
            <footer>
              <el-tag
                v-for="tag in fav.tags"
                :key="tag"
                size="small"
                effect="plain"
              >
                {{ tag }}
              </el-tag>
            </footer>
          </article>
        </div>
        <el-empty v-else description="收藏为空" />
      </el-tab-pane>

      <el-tab-pane label="设置" name="settings">
        <section class="setting-item">
          <div>
            <p>自动云同步</p>
            <small>在网络可用时后台增量同步</small>
          </div>
          <el-switch
            :model-value="store.cloudSync.auto"
            @change="handleAutoSync"
          />
        </section>

        <section class="setting-item">
          <div>
            <p>系统监控刷新频率</p>
            <small>{{ store.metrics.interval / 1000 }} 秒</small>
          </div>
          <el-slider
            :min="3000"
            :max="15000"
            :step="1000"
            :model-value="store.metrics.interval"
            @change="handleIntervalChange"
          />
        </section>

        <section class="setting-item">
          <div>
            <p>最新指标</p>
            <small v-if="metrics">CPU {{ metrics.overview.cpu }}% / 内存 {{ metrics.overview.memory }}%</small>
            <small v-else>等待采集...</small>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </aside>
</template>
