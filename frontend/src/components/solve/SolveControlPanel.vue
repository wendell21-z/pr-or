<template>
  <article class="card solve-card">
    <div class="card-head">
      <h4>启动排产</h4>
      <el-tag :type="solveState.running ? 'warning' : 'info'">
        {{ solveState.running ? '运行中' : '待命' }}
      </el-tag>
    </div>

    <el-form :model="form" label-width="88px">
      <el-form-item label="线体">
        <el-select v-model="form.lineId" placeholder="选择线体">
          <el-option
            v-for="item in lines"
            :key="item.id"
            :label="`${item.code} / ${item.description}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="form.begin" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>

      <div class="toolbar">
        <el-button type="primary" :loading="loading" @click="$emit('run')">开始排产</el-button>

        <el-button @click="$emit('refresh-status')">查询运行状态</el-button>
      </div>
    </el-form>

    <el-descriptions :column="1" border size="small">
      <el-descriptions-item label="运行中">
        {{ solveState.running ? '是' : '否' }}
      </el-descriptions-item>
      <el-descriptions-item label="线体">
        {{ solveState.lineId ?? '-' }}
      </el-descriptions-item>
    </el-descriptions>
  </article>
</template>

<script setup>
defineProps({
  form: {
    type: Object,
    required: true
  },
  lines: {
    type: Array,
    required: true
  },
  solveState: {
    type: Object,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['run', 'refresh-status'])
</script>

<style scoped>
.solve-card {
  min-height: 100%;
}

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
