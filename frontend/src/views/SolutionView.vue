<template>
  <div class="page-shell">
    <section class="page-hero">
      <p class="eyebrow">Solution Management</p>
      <h2>方案管理</h2>
      <p>管理固定任务、模具备注，并按时间范围查询排产结果。</p>
    </section>

    <section class="page-panel">
      <div class="panel-head">
        <div>
          <h3>方案维护</h3>
          <p>固定任务和备注作为人工干预入口，查询用于核对排产结果。</p>
        </div>
        <el-button @click="loadAll">刷新方案数据</el-button>
      </div>

      <div class="panel-grid">
        <article class="card">
          <div class="card-head">
            <h4>固定任务</h4>
            <el-tag>{{ tasks.length }}</el-tag>
          </div>
          <el-form :model="taskForm" label-width="88px">
            <el-form-item label="日期">
              <el-date-picker v-model="taskForm.day" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="模具">
              <el-select v-model="taskForm.dieId">
                <el-option v-for="item in dies" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="顺序">
              <el-input-number v-model="taskForm.seqInDay" :min="1" />
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="taskForm.quantity" :min="0" />
            </el-form-item>
            <el-button type="primary" @click="submitTask">新增</el-button>
          </el-form>
          <PaginatedTable :rows="tasks" :columns="taskColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeTask(row.taskId)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card">
          <div class="card-head">
            <h4>模具备注</h4>
            <el-tag>{{ memos.length }}</el-tag>
          </div>
          <el-form :model="memoForm" label-width="72px">
            <el-form-item label="模具">
              <el-select v-model="memoForm.dieId">
                <el-option v-for="item in dies" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="memoForm.content" type="textarea" :rows="3" />
            </el-form-item>
            <el-button type="primary" @click="submitMemo">新增</el-button>
          </el-form>
          <PaginatedTable :rows="memos" :columns="memoColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeMemo(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>按时间范围查询排产结果</h4>
            <el-tag>{{ queriedSolveResults.length }}</el-tag>
          </div>
          <el-form :model="queryForm" label-width="88px" class="grid-form">
            <el-form-item label="线体">
              <el-select v-model="queryForm.lineId">
                <el-option v-for="item in lines" :key="item.id" :label="item.code" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始">
              <el-date-picker v-model="queryForm.begin" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="结束">
              <el-date-picker v-model="queryForm.end" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-button type="primary" @click="querySolveResult">查询</el-button>
          </el-form>
          <PaginatedTable :rows="queriedSolveResults" :columns="resultColumns" :page-size="10" />
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PaginatedTable from '@/components/PaginatedTable.vue'
import { getDies, getLines } from '@/api/fact'
import { getSolveResultByWeek } from '@/api/solve'
import { addPinnedTask, deleteTask, deleteMemo, getMemos, saveMemo } from '@/api/solution'

const lines = ref([])
const dies = ref([])
const tasks = ref([])
const memos = ref([])
const queriedSolveResults = ref([])

const taskForm = reactive({ day: '', dieId: null, seqInDay: 1, quantity: 0 })
const memoForm = reactive({ dieId: null, content: '' })
const queryForm = reactive({ lineId: null, begin: '', end: '' })

const taskColumns = [
  { prop: 'taskId', label: '任务ID', width: 86 },
  { prop: 'day', label: '日期' },
  { prop: 'dieId', label: '模具' },
  { prop: 'seqInDay', label: '顺序' },
  { prop: 'quantity', label: '数量' },
  { label: '操作', width: 90, slot: 'actions' }
]

const memoColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'dieId', label: '模具', width: 80 },
  { prop: 'content', label: '内容' },
  { label: '操作', width: 90, slot: 'actions' }
]

const resultColumns = [
  { prop: 'lineId', label: '线体', width: 70 },
  { prop: 'day', label: '日期' },
  { prop: 'dieCode', label: '模具编码' },
  { prop: 'hits', label: '冲次数' },
  { prop: 'seqInDay', label: '顺序' }
]

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

function resetForm(form, values) {
  Object.keys(values).forEach((key) => {
    form[key] = values[key]
  })
}

async function loadAll() {
  const [ls, ds, memoResult] = await Promise.all([getLines(), getDies(), getMemos()])
  lines.value = normalizeList(ls)
  dies.value = normalizeList(ds)
  memos.value = normalizeList(memoResult, 'memos')
}

async function submitTask() {
  const result = await addPinnedTask({ ...taskForm })
  tasks.value = [{ ...taskForm, taskId: result.taskId }, ...tasks.value]
  ElMessage.success('固定任务已保存')
  resetForm(taskForm, { day: '', dieId: null, seqInDay: 1, quantity: 0 })
}

async function removeTask(id) {
  await deleteTask(id)
  tasks.value = tasks.value.filter((item) => item.taskId !== id)
  ElMessage.success('固定任务已删除')
}

async function submitMemo() {
  const result = await saveMemo({ ...memoForm })
  memos.value = [{ ...memoForm, id: result.id }, ...memos.value]
  ElMessage.success('备注已保存')
  resetForm(memoForm, { dieId: null, content: '' })
}

async function removeMemo(id) {
  await deleteMemo(id)
  memos.value = memos.value.filter((item) => item.id !== id)
  ElMessage.success('备注已删除')
}

async function querySolveResult() {
  const result = await getSolveResultByWeek(queryForm.lineId, queryForm.begin, queryForm.end)
  queriedSolveResults.value = normalizeList({
    data: (result?.tasks || []).map((item) => ({ ...item, lineId: result.lineId }))
  })
}

onMounted(loadAll)
</script>
