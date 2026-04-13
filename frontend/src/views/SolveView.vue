<template>
  <div class="page-shell">
    <section class="page-hero">
      <p class="eyebrow">Scheduling</p>
      <h2>排产求解</h2>
      <p>开始排产、查询状态，并查看最新与全量结果。</p>
    </section>

    <section class="page-panel">
      <div class="panel-head">
        <div>
          <h3>排产操作</h3>
          <p>当前页面专注于求解动作与结果查看。</p>
        </div>
        <div class="toolbar">
          <el-button @click="refreshSolveState">查询运行状态</el-button>
          <el-button @click="loadSolveResults">加载结果</el-button>
        </div>
      </div>

      <div class="panel-grid">
        <SolveControlPanel
          :form="solveForm"
          :lines="lines"
          :solve-state="solveState"
          :loading="solveLoading"
          @run="runSolve"
          @refresh-status="refreshSolveState"
        />

        <SolveLatestResult :rows="latestSolveResults" @refresh="loadLatestSolveResult" />

        <SolveResultTable
          title="全部排产结果"
          :rows="allSolveResults"
          refreshable
          @refresh="loadSolveResults"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLines } from '@/api/fact'
import {
  getAllSolveResults,
  getLatestSolveResult,
  isRunning,
  startSolve
} from '@/api/solve'
import SolveControlPanel from '@/components/solve/SolveControlPanel.vue'
import SolveLatestResult from '@/components/solve/SolveLatestResult.vue'
import SolveResultTable from '@/components/solve/SolveResultTable.vue'

const lines = ref([])
const latestSolveResults = ref([])
const allSolveResults = ref([])
const solveLoading = ref(false)
const solveForm = reactive({ lineId: null, begin: '' })
const solveState = reactive({ running: false, lineId: null })

function normalizeList(payload, key = 'data') {
  const list = payload?.[key]
  return Array.isArray(list)
    ? list.map((record) => {
        const next = { ...record }
        Object.keys(next).forEach((field) => {
          if (typeof next[field] === 'string' && /^\d{4}-\d{2}-\d{2}/.test(next[field])) {
            next[field] = next[field].slice(0, 10)
          }
        })
        return next
      })
    : []
}

async function loadLines() {
  const result = await getLines()
  lines.value = normalizeList(result)
}

async function refreshSolveState() {
  const result = await isRunning()
  solveState.running = Boolean(result?.running)
  solveState.lineId = result?.lineId ?? null
}

async function loadLatestSolveResult() {
  const result = await getLatestSolveResult()
  latestSolveResults.value = normalizeList(result)
}

async function loadSolveResults() {
  const result = await getAllSolveResults()
  allSolveResults.value = normalizeList(result)
}

async function runSolve() {
  solveLoading.value = true
  try {
    const result = await startSolve({ ...solveForm })

    if (result?.status === 'FAILED') {
      ElMessage.error(result?.message || '排产失败')
      if (result?.reasons && Array.isArray(result.reasons) && result.reasons.length) {
        ElMessage.info(result.reasons.join('; '))
      }
    } else if (result?.status === 'PARTIAL') {
      ElMessage.warning(result?.message || '部分排产结果已生成')
    } else {
      ElMessage.success(result?.message || '排产已启动')
    }

    // If backend returned immediate results, use them to populate UI without extra round-trip
    if (result?.results && Array.isArray(result.results) && result.results.length) {
      const normalized = normalizeList({ data: result.results })
      latestSolveResults.value = normalized.slice(0, 8)
      allSolveResults.value = normalized
      await refreshSolveState()
    } else {
      // Fallback: load from APIs
      await Promise.all([refreshSolveState(), loadLatestSolveResult(), loadSolveResults()])
    }
  } finally {
    solveLoading.value = false
  }
}



async function loadAll() {
  await Promise.all([loadLines(), refreshSolveState(), loadLatestSolveResult(), loadSolveResults()])
}

onMounted(loadAll)
</script>
