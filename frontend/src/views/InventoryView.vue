<template>
  <div class="page-shell">
    <section class="page-hero">
      <p class="eyebrow">Inventory And Demand</p>
      <h2>库存需求</h2>
      <p>维护器具、器具库存、零件库存和车身流数据。</p>
    </section>

    <section class="page-panel">
      <div class="panel-head">
        <div>
          <h3>库存与需求</h3>
          <p>这些数据会直接影响排产输入和结果。</p>
        </div>
        <el-button @click="loadAll">刷新数据</el-button>
      </div>

      <div class="panel-grid">
        <article class="card">
          <div class="card-head">
            <h4>器具</h4>
            <el-tag>{{ dunnages.length }}</el-tag>
          </div>
          <el-form :model="dunnageForm" label-width="72px">
            <el-form-item label="名称">
              <el-input v-model="dunnageForm.name" />
            </el-form-item>
            <el-form-item label="容量">
              <el-input-number v-model="dunnageForm.capacity" :min="1" />
            </el-form-item>
            <el-button type="primary" @click="submitDunnage">新增</el-button>
          </el-form>
          <PaginatedTable :rows="dunnages" :columns="dunnageColumns" :page-size="8">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeDunnage(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>器具库存</h4>
            <el-tag>{{ dunnageInventories.length }}</el-tag>
          </div>
          <el-form :model="dunnageInventoryForm" label-width="88px" class="grid-form">
            <el-form-item label="日期">
              <el-date-picker v-model="dunnageInventoryForm.day" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="器具">
              <el-select v-model="dunnageInventoryForm.dunnageId">
                <el-option v-for="item in dunnages" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="总数">
              <el-input-number v-model="dunnageInventoryForm.quantity" :min="0" />
            </el-form-item>
            <el-form-item label="空箱">
              <el-input-number v-model="dunnageInventoryForm.emptyQuantity" :min="0" />
            </el-form-item>
            <el-form-item label="维修">
              <el-input-number v-model="dunnageInventoryForm.repairQuantity" :min="0" />
            </el-form-item>
            <el-form-item label="封存">
              <el-input-number v-model="dunnageInventoryForm.sealedQuantity" :min="0" />
            </el-form-item>
            <el-form-item label="待修">
              <el-input-number v-model="dunnageInventoryForm.pendingRepairQuantity" :min="0" />
            </el-form-item>
            <el-form-item label="焊接">
              <el-input-number v-model="dunnageInventoryForm.weldingQuantity" :min="0" />
            </el-form-item>
            <el-button type="primary" @click="submitDunnageInventory">新增</el-button>
          </el-form>
          <PaginatedTable :rows="dunnageInventories" :columns="dunnageInventoryColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeDunnageInventory(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card wide">
          <div class="card-head">
            <h4>零件库存</h4>
            <el-tag>{{ partInventories.length }}</el-tag>
          </div>
          <el-form :model="partInventoryForm" label-width="72px" class="grid-form">
            <el-form-item label="零件">
              <el-select v-model="partInventoryForm.part">
                <el-option v-for="item in parts" :key="item.id" :label="item.code" :value="item.code" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期">
              <el-date-picker v-model="partInventoryForm.day" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="partInventoryForm.quantity" :min="0" />
            </el-form-item>
            <el-button type="primary" @click="submitPartInventory">新增</el-button>
          </el-form>
          <PaginatedTable :rows="partInventories" :columns="partInventoryColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removePartInventory(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>

        <article class="card">
          <div class="card-head">
            <h4>车身流</h4>
            <el-tag>{{ carUsages.length }}</el-tag>
          </div>
          <el-form :model="carUsageForm" label-width="72px">
            <el-form-item label="车型">
              <el-select v-model="carUsageForm.carId">
                <el-option v-for="item in cars" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期">
              <el-date-picker v-model="carUsageForm.day" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="carUsageForm.num" :min="0" />
            </el-form-item>
            <el-button type="primary" @click="submitCarUsage">新增</el-button>
          </el-form>
          <PaginatedTable :rows="carUsages" :columns="carUsageColumns" :page-size="10">
            <template #actions="{ row }">
              <el-button link type="danger" @click="removeCarUsage(row.id)">删除</el-button>
            </template>
          </PaginatedTable>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PaginatedTable from '@/components/PaginatedTable.vue'
import {
  getCars,
  getParts,
  getDunnages,
  saveDunnage,
  deleteDunnage,
  getDunnageInventories,
  saveDunnageInventory,
  deleteDunnageInventory,
  getPartInventories,
  savePartInventory,
  deletePartInventory,
  getCarUsages,
  saveCarUsage,
  deleteCarUsage
} from '@/api/fact'

const dunnages = ref([])
const dunnageInventories = ref([])
const partInventories = ref([])
const carUsages = ref([])
const cars = ref([])
const parts = ref([])

const dunnageForm = reactive({ name: '', capacity: 1 })
const dunnageInventoryForm = reactive({
  day: '',
  dunnageId: null,
  quantity: 0,
  emptyQuantity: 0,
  repairQuantity: 0,
  sealedQuantity: 0,
  pendingRepairQuantity: 0,
  weldingQuantity: 0
})
const partInventoryForm = reactive({ part: '', day: '', quantity: 0 })
const carUsageForm = reactive({ carId: null, day: '', num: 0 })

const dunnageColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'name', label: '名称' },
  { prop: 'capacity', label: '容量' },
  { label: '操作', width: 90, slot: 'actions' }
]

const dunnageInventoryColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'day', label: '日期' },
  { prop: 'dunnageId', label: '器具' },
  { prop: 'quantity', label: '总数' },
  { prop: 'emptyQuantity', label: '空箱' },
  { label: '操作', width: 90, slot: 'actions' }
]

const partInventoryColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'part', label: '零件编码' },
  { prop: 'day', label: '日期' },
  { prop: 'quantity', label: '数量' },
  { label: '操作', width: 90, slot: 'actions' }
]

const carUsageColumns = [
  { prop: 'id', label: 'ID', width: 70 },
  { prop: 'carId', label: '车型' },
  { prop: 'day', label: '日期' },
  { prop: 'num', label: '数量' },
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
  const [du, dui, pi, cu, ca, pa] = await Promise.all([
    getDunnages(),
    getDunnageInventories(),
    getPartInventories(),
    getCarUsages(),
    getCars(),
    getParts()
  ])
  dunnages.value = normalizeList(du)
  dunnageInventories.value = normalizeList(dui)
  partInventories.value = normalizeList(pi)
  carUsages.value = normalizeList(cu)
  cars.value = normalizeList(ca)
  parts.value = normalizeList(pa)
}

async function submitDunnage() {
  await saveDunnage({ ...dunnageForm })
  ElMessage.success('器具已保存')
  resetForm(dunnageForm, { name: '', capacity: 1 })
  await loadAll()
}

async function removeDunnage(id) {
  await deleteDunnage(id)
  ElMessage.success('器具已删除')
  await loadAll()
}

async function submitDunnageInventory() {
  await saveDunnageInventory({ ...dunnageInventoryForm })
  ElMessage.success('器具库存已保存')
  resetForm(dunnageInventoryForm, {
    day: '',
    dunnageId: null,
    quantity: 0,
    emptyQuantity: 0,
    repairQuantity: 0,
    sealedQuantity: 0,
    pendingRepairQuantity: 0,
    weldingQuantity: 0
  })
  await loadAll()
}

async function removeDunnageInventory(id) {
  await deleteDunnageInventory(id)
  ElMessage.success('器具库存已删除')
  await loadAll()
}

async function submitPartInventory() {
  await savePartInventory({ ...partInventoryForm })
  ElMessage.success('零件库存已保存')
  resetForm(partInventoryForm, { part: '', day: '', quantity: 0 })
  await loadAll()
}

async function removePartInventory(id) {
  await deletePartInventory(id)
  ElMessage.success('零件库存已删除')
  await loadAll()
}

async function submitCarUsage() {
  await saveCarUsage({ ...carUsageForm })
  ElMessage.success('车身流已保存')
  resetForm(carUsageForm, { carId: null, day: '', num: 0 })
  await loadAll()
}

async function removeCarUsage(id) {
  await deleteCarUsage(id)
  ElMessage.success('车身流已删除')
  await loadAll()
}

onMounted(loadAll)
</script>
