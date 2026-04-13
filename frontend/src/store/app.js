import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const loading = ref(false)
  
  // Basic data cache
  const lines = ref([])
  const dies = ref([])
  const parts = ref([])
  const cars = ref([])
  const dunnages = ref([])
  const workingTimes = ref([])
  const days = ref([])
  
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
  
  function setLoading(val) {
    loading.value = val
  }
  
  return {
    sidebarCollapsed,
    loading,
    lines,
    dies,
    parts,
    cars,
    dunnages,
    workingTimes,
    days,
    toggleSidebar,
    setLoading
  }
})
