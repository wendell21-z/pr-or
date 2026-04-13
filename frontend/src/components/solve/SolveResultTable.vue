<template>
  <article class="card wide">
    <div class="card-head">
      <h4>{{ title }}</h4>
      <div class="toolbar">
        <el-tag>{{ rows.length }}</el-tag>
        <el-button v-if="refreshable" @click="$emit('refresh')">刷新结果</el-button>
      </div>
    </div>

    <PaginatedTable :rows="rows" :columns="columns" :page-size="10" />
  </article>
</template>

<script setup>
import PaginatedTable from '@/components/PaginatedTable.vue'

defineProps({
  title: {
    type: String,
    default: '全部排产结果'
  },
  rows: {
    type: Array,
    required: true
  },
  refreshable: {
    type: Boolean,
    default: false
  }
})

defineEmits(['refresh'])

const columns = [
  { prop: 'lineId', label: '线体', width: 70 },
  { prop: 'day', label: '日期' },
  { prop: 'dieCode', label: '模具编码' },
  { prop: 'hits', label: '冲次数' },
  { prop: 'startTime', label: '开始分钟' },
  { prop: 'seqInDay', label: '顺序' }
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
