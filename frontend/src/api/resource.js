import request from './request'

// Resource APIs
export function getProductionResources(params) {
  return request.get('/jvs-aps/production-resource/page', { params })
}

export function createProductionResource(data) {
  return request.post('/jvs-aps/production-resource', data)
}

export function updateProductionResource(data) {
  return request.put('/jvs-aps/production-resource', data)
}

export function getResourceGroupList() {
  return request.get('/jvs-aps/production-resource/group/list')
}

// Material APIs
export function getMaterials(params) {
  return request.get('/jvs-aps/material/page', { params })
}

export function createMaterial(data) {
  return request.post('/jvs-aps/material', data)
}

export function updateMaterial(data) {
  return request.put('/jvs-aps/material', data)
}

export function deleteMaterial(id) {
  return request.delete(`/jvs-aps/material/${id}`)
}

// Process APIs
export function createProcess(data) {
  return request.post('/jvs-aps/process', data)
}

export function getProcess(id) {
  return request.get(`/jvs-aps/process/${id}`)
}

export function updateProcess(data) {
  return request.put('/jvs-aps/process', data)
}

export function getProcesses(params) {
  return request.get('/jvs-aps/process/page', { params })
}

// Smart Scheduling APIs
export function cancelPendingPlan(data) {
  return request.post('/jvs-aps/smart-scheduling/plan/pending/cancel', data)
}

export function confirmPendingPlan(data) {
  return request.post('/jvs-aps/smart-scheduling/plan/pending/confirm', data)
}
