<template>
  <div class="paginated-table">
    <el-table :data="pagedRows" size="small" v-bind="$attrs">
      <el-table-column
        v-for="column in columns"
        :key="column.prop || column.label"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth"
      >
        <template v-if="column.slot" #default="{ row, $index }">
          <slot :name="column.slot" :row="row" :index="$index" />
        </template>
        <template v-else-if="column.prop" #default="{ row }">
          <slot :name="`cell-${column.prop}`" :row="row" :value="row[column.prop]">
            {{ row[column.prop] }}
          </slot>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="rows.length > internalPageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="internalPageSize"
        background
        layout="total, sizes, prev, pager, next"
        :total="rows.length"
        :page-sizes="pageSizes"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  rows: {
    type: Array,
    required: true
  },
  columns: {
    type: Array,
    required: true
  },
  pageSize: {
    type: Number,
    default: 10
  },
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  }
})

const currentPage = ref(1)
const internalPageSize = ref(props.pageSize)

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * internalPageSize.value
  return props.rows.slice(start, start + internalPageSize.value)
})

watch(
  () => props.rows.length,
  () => {
    const maxPage = Math.max(1, Math.ceil(props.rows.length / internalPageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
    }
  }
)
</script>

<style scoped>
.paginated-table {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
}
</style>
