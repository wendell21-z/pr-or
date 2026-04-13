<template>
  <div class="page-shell">
    <section class="page-hero">
      <p class="eyebrow">Master Data</p>
      <h2>基础数据</h2>
      <p>管理工作时间、日期、线体、模具、零件、车型以及车型零件关系。</p>
    </section>

    <section class="page-panel">
      <div class="panel-head">
        <div>
          <h3>基础资料维护</h3>
          <p>变更后会直接调用后端接口写入数据库。</p>
        </div>
        <el-button @click="loadAll">刷新数据</el-button>
      </div>

      <div class="panel-grid">
        <article class="card">
          <div class="card-head">
            <h4>工作时间</h4>
            <el-tag>{{ workingTimes.length }}</el-tag>
          </div>
          <el-form :model="workingTimeForm" label-width="72px">
            <el-form-item label="名称">
              <el-input v-model="workingTimeForm.text" />
            </el-form-item>
            <el-form-item label="分钟">
              <el-input-number v-model="workingTimeForm.minutes" :min="1" />
            </el-form-item>
            <el-button type="primary" @click="submitWorkingTime">新增</el-button>
          </el-form>
          <PaginatedTable :rows="workingTimes" :columns="workingTimeColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeWorkingTime(row.text)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card">
          <div class="card-head">
            <h4>日期配置</h4>
            <el-tag>{{ days.length }}</el-tag>
          </div>
          <el-form :model="dayForm" label-width="72px">
            <el-form-item label="日期">
              <el-date-picker v-model="dayForm.day" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="工时">
              <el-select v-model="dayForm.workingTimeText">
                <el-option v-for="item in workingTimes" :key="item.text" :label="item.text" :value="item.text" />
              </el-select>
            </el-form-item>
            <el-form-item label="停机">
              <el-input-number v-model="dayForm.outMinutes" :min="0" />
            </el-form-item>
            <el-button type="primary" @click="submitDay">新增</el-button>
          </el-form>
          <PaginatedTable :rows="days" :columns="dayColumns" :page-size="8" />
        </article>

        <article class="card">
          <div class="card-head">
            <h4>线体</h4>
            <el-tag>{{ lines.length }}</el-tag>
          </div>
          <el-form :model="lineForm" label-width="72px">
            <el-form-item label="编码">
              <el-input v-model="lineForm.code" />
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="lineForm.description" />
            </el-form-item>
            <el-button type="primary" @click="submitLine">新增</el-button>
          </el-form>
          <PaginatedTable :rows="lines" :columns="lineColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeLine(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>模具</h4>
            <el-tag>{{ dies.length }}</el-tag>
          </div>
          <el-form :model="dieForm" label-width="72px" class="grid-form">
            <el-form-item label="编码">
              <el-input v-model="dieForm.code" />
            </el-form-item>
            <el-form-item label="名称">
              <el-input v-model="dieForm.name" />
            </el-form-item>
            <el-form-item label="AKZ">
              <el-input-number v-model="dieForm.akz" :min="1" />
            </el-form-item>
            <el-form-item label="线体">
              <el-select v-model="dieForm.lineId">
                <el-option v-for="item in lines" :key="item.id" :label="item.code" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" @click="submitDie">新增</el-button>
          </el-form>
          <PaginatedTable :rows="dies" :columns="dieColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeDie(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>零件</h4>
            <el-tag>{{ parts.length }}</el-tag>
          </div>
          <el-form :model="partForm" label-width="72px" class="grid-form">
            <el-form-item label="编码">
              <el-input v-model="partForm.code" />
            </el-form-item>
            <el-form-item label="名称">
              <el-input v-model="partForm.name" />
            </el-form-item>
            <el-form-item label="最小库存">
              <el-input-number v-model="partForm.min" :min="0" />
            </el-form-item>
            <el-form-item label="模具">
              <el-select v-model="partForm.dieId">
                <el-option v-for="item in dies" :key="item.id" :label="item.code" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="器具">
              <el-select v-model="partForm.dunnageId">
                <el-option v-for="item in dunnages" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-button type="primary" @click="submitPart">新增</el-button>
          </el-form>
          <PaginatedTable :rows="parts" :columns="partColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removePart(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card">
          <div class="card-head">
            <h4>车型</h4>
            <el-tag>{{ cars.length }}</el-tag>
          </div>
          <el-form :model="carForm" label-width="72px">
            <el-form-item label="编码">
              <el-input v-model="carForm.code" />
            </el-form-item>
            <el-form-item label="名称">
              <el-input v-model="carForm.name" />
            </el-form-item>
            <el-button type="primary" @click="submitCar">新增</el-button>
          </el-form>
          <PaginatedTable :rows="cars" :columns="carColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeCar(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card">
          <div class="card-head">
            <h4>车型零件关系</h4>
            <el-tag>{{ carParts.length }}</el-tag>
          </div>
          <el-form :model="carPartForm" label-width="72px">
            <el-form-item label="车型">
              <el-select v-model="carPartForm.carId">
                <el-option v-for="item in cars" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="零件">
              <el-select v-model="carPartForm.partId">
                <el-option v-for="item in parts" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="单车用量">
              <el-input-number v-model="carPartForm.usage" :min="1" />
            </el-form-item>
            <el-button type="primary" @click="submitCarPart">新增</el-button>
          </el-form>
          <PaginatedTable :rows="carParts" :columns="carPartColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeCarPart(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import PaginatedTable from '@/components/PaginatedTable.vue'
import {
  getWorkingTimes,
  saveWorkingTime,
  deleteWorkingTime,
  getDays,
  saveDay,
  getLines,
  saveLine,
  deleteLine,
  getDies,
  saveDie,
  deleteDie,
  getParts,
  savePart,
  deletePart,
  getCars,
  saveCar,
  deleteCar,
  getCarParts,
  saveCarPart,
  deleteCarPart,
  getDunnages
} from '@/api/fact'

const workingTimes = ref([])
const days = ref([])
const lines = ref([])
const dies = ref([])
const parts = ref([])
const cars = ref([])
const carParts = ref([])
const dunnages = ref([])

const workingTimeForm = reactive({ text: '', minutes: 480 })
const dayForm = reactive({ day: '', workingTimeText: '', outMinutes: 0 })
const lineForm = reactive({ code: '', description: '' })
const dieForm = reactive({ code: '', name: '', akz: 1, lineId: null })
const partForm = reactive({ code: '', name: '', min: 0, dieId: null, dunnageId: null })
const carForm = reactive({ code: '', name: '' })
const carPartForm = reactive({ carId: null, partId: null, usage: 1 })

const workingTimeColumns = [
  { prop: 'text', label: '名称' },
  { prop: 'minutes', label: '分钟' },
  { label: '操作', width: 90, slot: 'actions' }
]

const dayColumns = [
  { prop: 'day', label: '日期' },
  { prop: 'workingTimeText', label: '工时' },
  { prop: 'outMinutes', label: '停机分钟' }
]

const lineColumns = [
  { prop: 'id', label: 'ID', width: 80 },
  { prop: 'code', label: '编码' },
  { prop: 'description', label: '描述' },
  { label: '操作', width: 90, slot: 'actions' }
]

const dieColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'code', label: '编码' },
  { prop: 'name', label: '名称' },
  { prop: 'akz', label: 'AKZ', width: 80 },
  { prop: 'lineId', label: '线体', width: 80 },
  { label: '操作', width: 90, slot: 'actions' }
]

const partColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'code', label: '编码' },
  { prop: 'name', label: '名称' },
  { prop: 'min', label: '最小库存', width: 100 },
  { prop: 'dieId', label: '模具', width: 80 },
  { prop: 'dunnageId', label: '器具', width: 80 },
  { label: '操作', width: 90, slot: 'actions' }
]

const carColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'code', label: '编码' },
  { prop: 'name', label: '名称' },
  { label: '操作', width: 90, slot: 'actions' }
]

const carPartColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'carId', label: '车型' },
  { prop: 'partId', label: '零件' },
  { prop: 'usage', label: '用量' },
  { label: '操作', width: 90, slot: 'actions' }
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
  const [wt, ds, ls, di, pa, ca, cp, du] = await Promise.all([
    getWorkingTimes(),
    getDays(),
    getLines(),
    getDies(),
    getParts(),
    getCars(),
    getCarParts(),
    getDunnages()
  ])
  workingTimes.value = normalizeList(wt)
  days.value = normalizeList(ds)
  lines.value = normalizeList(ls)
  dies.value = normalizeList(di)
  parts.value = normalizeList(pa)
  cars.value = normalizeList(ca)
  carParts.value = normalizeList(cp)
  dunnages.value = normalizeList(du)
}

async function submitWorkingTime() {
  await saveWorkingTime({ ...workingTimeForm })
  ElMessage.success('工作时间已保存')
  resetForm(workingTimeForm, { text: '', minutes: 480 })
  await loadAll()
}

async function removeWorkingTime(text) {
  await deleteWorkingTime(text)
  ElMessage.success('工作时间已删除')
  await loadAll()
}

async function submitDay() {
  await saveDay({ ...dayForm })
  ElMessage.success('日期配置已保存')
  resetForm(dayForm, { day: '', workingTimeText: '', outMinutes: 0 })
  await loadAll()
}

async function submitLine() {
  await saveLine({ ...lineForm })
  ElMessage.success('线体已保存')
  resetForm(lineForm, { code: '', description: '' })
  await loadAll()
}

async function removeLine(id) {
  await deleteLine(id)
  ElMessage.success('线体已删除')
  await loadAll()
}

async function submitDie() {
  await saveDie({ ...dieForm })
  ElMessage.success('模具已保存')
  resetForm(dieForm, { code: '', name: '', akz: 1, lineId: null })
  await loadAll()
}

async function removeDie(id) {
  await deleteDie(id)
  ElMessage.success('模具已删除')
  await loadAll()
}

async function submitPart() {
  await savePart({ ...partForm })
  ElMessage.success('零件已保存')
  resetForm(partForm, { code: '', name: '', min: 0, dieId: null, dunnageId: null })
  await loadAll()
}

async function removePart(id) {
  await deletePart(id)
  ElMessage.success('零件已删除')
  await loadAll()
}

async function submitCar() {
  await saveCar({ ...carForm })
  ElMessage.success('车型已保存')
  resetForm(carForm, { code: '', name: '' })
  await loadAll()
}

async function removeCar(id) {
  await deleteCar(id)
  ElMessage.success('车型已删除')
  await loadAll()
}

async function submitCarPart() {
  await saveCarPart({ ...carPartForm })
  ElMessage.success('车型零件关系已保存')
  resetForm(carPartForm, { carId: null, partId: null, usage: 1 })
  await loadAll()
}

async function removeCarPart(id) {
  await deleteCarPart(id)
  ElMessage.success('车型零件关系已删除')
  await loadAll()
}

onMounted(loadAll)
</script>
