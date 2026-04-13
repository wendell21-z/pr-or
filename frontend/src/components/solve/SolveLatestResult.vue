<template>
  <article class="card">
    <div class="card-head">
      <h4>最新结果预览</h4>
      <div class="toolbar">
        <el-tag>{{ rows.length }}</el-tag>
        <el-button link type="primary" @click="$emit('refresh')">刷新</el-button>
      </div>
    </div>

    <PaginatedTable
      :rows="rows"
      :columns="columns"
      :page-size="8"
      max-height="360"
    />
  </article>
</template>

<script setup>
import PaginatedTable from '@/components/PaginatedTable.vue'

defineProps({
  rows: {
    type: Array,
    required: true
  }
})

defineEmits(['refresh'])

const columns = [
  { prop: 'lineId', label: '线体', width: 80 },
  { prop: 'day', label: '日期' },
  { prop: 'dieCode', label: '模具' },
  { prop: 'hits', label: '冲次数' },
  { prop: 'seqInDay', label: '日内顺序' }
]
</script>

<style scoped>
.card-head,
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-head {
  margin-bottom: 12px;
}

.card-head h4 {
  margin: 0;
}
</style>
