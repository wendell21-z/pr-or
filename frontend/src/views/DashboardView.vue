<template>
  <div class="page-shell">
    <section class="page-hero">
      <p class="eyebrow">Factory Scheduling Workspace</p>
      <h2>排产工作台</h2>
      <p>把核心数据、排产状态和结果摘要放在首页，方便进入不同功能页面继续操作。</p>
    </section>

    <section class="stats-grid">
      <article v-for="item in stats" :key="item.label" class="stats-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </section>

    <section class="page-panel">
      <div class="panel-head">
        <div>
          <h3>系统状态</h3>
          <p>当前排产状态与最新结果预览。</p>
        </div>
        <div class="toolbar">
          <el-button @click="loadAll">刷新</el-button>
          <el-tag :type="solveState.running ? 'warning' : 'success'">
            {{ solveState.running ? '排产运行中' : '排产空闲' }}
          </el-tag>
        </div>
      </div>

      <div class="panel-grid">
        <article class="card">
          <div class="card-head">
            <h4>运行状态</h4>
          </div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="运行中">{{ solveState.running ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="线体">{{ solveState.lineId ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>最新排产结果</h4>
            <el-tag>{{ latestSolveResults.length }}</el-tag>
          </div>
          <el-table :data="latestSolveResults" size="small">
            <el-table-column prop="lineId" label="线体" width="80" />
            <el-table-column prop="day" label="日期" />
            <el-table-column prop="dieCode" label="模具" />
            <el-table-column prop="hits" label="冲次数" />
            <el-table-column prop="seqInDay" label="顺序" />
          </el-table>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  getLines,
  getDies,
  getParts,
  getCars,
  getPartInventories,
  getCarUsages
} from '@/api/fact'
import { getLatestSolveResult, isRunning } from '@/api/solve'

const lines = ref([])
const dies = ref([])
const parts = ref([])
const cars = ref([])
const partInventories = ref([])
const carUsages = ref([])
const latestSolveResults = ref([])
const solveState = reactive({ running: false, lineId: null })

const stats = computed(() => [
  { label: '线体', value: lines.value.length },
  { label: '模具', value: dies.value.length },
  { label: '零件', value: parts.value.length },
  { label: '车型', value: cars.value.length },
  { label: '库存记录', value: partInventories.value.length },
  { label: '车身流', value: carUsages.value.length }
])

function normalizeList(payload, key = 'data') {
  return Array.isArray(payload?.[key])
    ? payload[key].map((item) => {
        const next = { ...item }
        Object.keys(next).forEach((field) => {
          if (typeof next[field] === 'string' && /^\d{4}-\d{2}-\d{2}/.test(next[field])) {
            next[field] = next[field].slice(0, 10)
          }
        })
        return next
      })
    : []
}

async function loadAll() {
  const [ls, ds, ps, cs, pis, cus, latest, running] = await Promise.all([
    getLines(),
    getDies(),
    getParts(),
    getCars(),
    getPartInventories(),
    getCarUsages(),
    getLatestSolveResult(),
    isRunning()
  ])
  lines.value = normalizeList(ls)
  dies.value = normalizeList(ds)
  parts.value = normalizeList(ps)
  cars.value = normalizeList(cs)
  partInventories.value = normalizeList(pis)
  carUsages.value = normalizeList(cus)
  latestSolveResults.value = normalizeList(latest)
  solveState.running = Boolean(running?.running)
  solveState.lineId = running?.lineId ?? null
}

onMounted(loadAll)
</script>
