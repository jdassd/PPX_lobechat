<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ToolCard from '../ToolCard.vue'
import { useToolkitStore } from '@/stores/toolkit'
import dayjs from '@/utils/dayjs'

const store = useToolkitStore()

const drawerVisible = computed({
  get: () => store.activeDrawer === 'clipboard',
  set: (val) => {
    if (!val) {
      store.closeDrawer()
    }
  }
})

const lastItem = computed(() => store.clipboard.items[0])
const items = computed(() => store.filteredClipboardItems)
const availableTags = computed(() => store.availableClipboardTags)

const manualForm = reactive({
  type: 'text',
  content: ''
})
const tagDraft = reactive({})

const handleManualSave = async () => {
  if (!manualForm.content.trim()) {
    return
  }
  await store.manualClipboardSave(manualForm.content.trim(), manualForm.type)
  manualForm.content = ''
}

const copyItem = async (item) => {
  if (item.type === 'image') {
    try {
      const link = document.createElement('a')
      link.href = item.content
      link.download = `clip-${item.id}.png`
      link.click()
      ElMessage.success('已保存图片')
    } catch (err) {
      ElMessage.error('保存失败')
    }
    return
  }
  try {
    await navigator.clipboard.writeText(item.content)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}

const handleAddTag = (itemId) => {
  const value = tagDraft[itemId]
  if (!value) {
    return
  }
  store.addClipboardTag(itemId, value.trim())
  tagDraft[itemId] = ''
}
</script>

<template>
  <ToolCard
    title="多格式剪贴板"
    subtitle="文本 / 链接 / 图片"
    badge="实时"
    tone="blue"
  >
    <div class="card-stats">
      <div>
        <p>累计记录</p>
        <strong>{{ store.clipboardCount }}</strong>
      </div>
      <div>
        <p>收藏</p>
        <strong>{{ store.favoriteClipboardItems.length }}</strong>
      </div>
      <div>
        <p>最近记录</p>
        <span>{{ lastItem?.summary || '暂无数据' }}</span>
      </div>
    </div>
    <template #actions>
      <el-button
        size="small"
        type="primary"
        plain
        :loading="store.clipboard.syncing"
        @click="store.captureClipboard"
      >
        捕获剪贴板
      </el-button>
      <el-button
        size="small"
        text
        @click="store.openDrawer('clipboard')"
      >
        扩展视图
      </el-button>
    </template>
  </ToolCard>

  <el-drawer
    title="剪贴板历史"
    v-model="drawerVisible"
    destroy-on-close
    size="45%"
    @close="store.closeDrawer"
  >
    <section class="drawer-section">
      <header class="drawer-section__header">
        <h3>新增内容</h3>
        <el-radio-group v-model="manualForm.type" size="small">
          <el-radio-button label="text">文本</el-radio-button>
          <el-radio-button label="link">链接</el-radio-button>
          <el-radio-button label="image">图片</el-radio-button>
        </el-radio-group>
      </header>
      <el-input
        v-model="manualForm.content"
        type="textarea"
        placeholder="粘贴或输入内容"
        :rows="3"
      />
      <div class="drawer-actions">
        <el-button @click="manualForm.content = ''">清空</el-button>
        <el-button type="primary" @click="handleManualSave">保存到历史</el-button>
      </div>
    </section>

    <section class="drawer-section">
      <header class="drawer-section__header">
        <h3>历史记录</h3>
        <el-input
          v-model="store.clipboard.search"
          size="small"
          placeholder="搜索内容或标签"
          prefix-icon="ele-Search"
          @input="store.setClipboardSearch(store.clipboard.search)"
        />
      </header>

      <div class="filter-row">
        <el-radio-group
          v-model="store.clipboard.filter"
          size="small"
          @change="store.setClipboardFilter"
        >
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="text">文本</el-radio-button>
          <el-radio-button label="link">链接</el-radio-button>
          <el-radio-button label="image">图片</el-radio-button>
          <el-radio-button label="favorite">收藏</el-radio-button>
        </el-radio-group>
        <el-select
          v-model="store.clipboard.activeTag"
          size="small"
          clearable
          placeholder="标签筛选"
          style="width: 140px"
          @change="store.setClipboardTag"
        >
          <el-option
            v-for="tag in availableTags"
            :key="tag"
            :value="tag"
            :label="tag"
          />
        </el-select>
      </div>

      <el-alert
        v-if="store.clipboard.lastError"
        type="error"
        :title="store.clipboard.lastError"
        show-icon
        class="mb10"
      />

      <el-empty v-if="!items.length" description="暂无记录" />

      <div v-else class="clipboard-list">
        <article
          v-for="item in items"
          :key="item.id"
          class="clipboard-item"
        >
          <header>
            <div>
              <el-tag size="small" type="info">{{ item.type }}</el-tag>
              <small>{{ dayjs(item.createdAt).fromNow() }}</small>
            </div>
            <div class="actions">
              <el-button text size="small" @click="copyItem(item)">复制</el-button>
              <el-button text size="small" @click="store.toggleClipboardFavorite(item.id)">
                {{ item.favorite ? '取消收藏' : '收藏' }}
              </el-button>
              <el-button text size="small" @click="store.removeClipboardItem(item.id)">删除</el-button>
            </div>
          </header>
          <p v-if="item.type !== 'image'">{{ item.content }}</p>
          <img v-else :src="item.content" alt="剪贴板图片" />
          <footer>
            <div class="tags">
              <el-tag
                v-for="tag in item.tags"
                :key="tag"
                size="small"
                closable
                @close="store.removeClipboardTag(item.id, tag)"
              >
                {{ tag }}
              </el-tag>
            </div>
            <div class="add-tag">
              <el-input
                v-model="tagDraft[item.id]"
                size="small"
                placeholder="标签"
                @keyup.enter="handleAddTag(item.id)"
              />
              <el-button size="small" @click="handleAddTag(item.id)">添加</el-button>
            </div>
          </footer>
        </article>
      </div>
    </section>
  </el-drawer>
</template>
