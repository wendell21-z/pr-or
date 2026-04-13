import request from './request'

// Working Time APIs
export function getWorkingTimes() {
  return request.get('/fact/working-time')
}

export function saveWorkingTime(data) {
  return request.post('/fact/working-time', data)
}

export function deleteWorkingTime(text) {
  return request.delete(`/fact/working-time/${text}`)
}

// Day APIs
export function getDays() {
  return request.get('/fact/day')
}

export function saveDay(data) {
  return request.post('/fact/day', data)
}

export function batchSaveDays(data) {
  return request.post('/fact/day/batch', data)
}

// Line APIs
export function getLines() {
  return request.get('/fact/line')
}

export function saveLine(data) {
  return request.post('/fact/line', data)
}

export function deleteLine(id) {
  return request.delete(`/fact/line/${id}`)
}

// Die APIs
export function getDies() {
  return request.get('/fact/die/all')
}

export function saveDie(data) {
  return request.post('/fact/die', data)
}

export function batchSaveDies(data) {
  return request.post('/fact/die/batch', data)
}

export function deleteDie(id) {
  return request.delete(`/fact/die/${id}`)
}

// Part APIs
export function getParts() {
  return request.get('/fact/part/all')
}

export function savePart(data) {
  return request.post('/fact/part', data)
}

export function deletePart(id) {
  return request.delete(`/fact/part/${id}`)
}

// Car APIs
export function getCars() {
  return request.get('/fact/car/all')
}

export function saveCar(data) {
  return request.post('/fact/car', data)
}

export function deleteCar(id) {
  return request.delete(`/fact/car/${id}`)
}

// Car-Part Relationship APIs
export function getCarParts() {
  return request.get('/fact/part-car')
}

export function saveCarPart(data) {
  return request.post('/fact/part-car', data)
}

export function deleteCarPart(id) {
  return request.delete(`/fact/part-car/${id}`)
}

// Part Inventory APIs
export function getPartInventories() {
  return request.get('/fact/part-inventory/all')
}

export function savePartInventory(data) {
  return request.post('/fact/part-inventory', data)
}

export function batchSavePartInventories(data) {
  return request.post('/fact/part-inventory/batch', data)
}

export function deletePartInventory(id) {
  return request.delete(`/fact/part-inventory/${id}`)
}

// Dunnage APIs
export function getDunnages() {
  return request.get('/fact/dunnage')
}

export function saveDunnage(data) {
  return request.post('/fact/dunnage', data)
}

export function batchSaveDunnages(data) {
  return request.post('/fact/dunnage/batch', data)
}

export function deleteDunnage(id) {
  return request.delete(`/fact/dunnage/${id}`)
}

// Dunnage Inventory APIs
export function getDunnageInventories() {
  return request.get('/fact/dunnage-inventory/all')
}

export function getLatestDunnageInventory() {
  return request.get('/fact/dunnage-inventory/latest')
}

export function saveDunnageInventory(data) {
  return request.post('/fact/dunnage-inventory', data)
}

export function batchSaveDunnageInventories(data) {
  return request.post('/fact/dunnage-inventory/batch', data)
}

export function deleteDunnageInventory(id) {
  return request.delete(`/fact/dunnage-inventory/${id}`)
}

// Car Usage APIs
export function getCarUsages() {
  return request.get('/fact/car-usage/all')
}

export function saveCarUsage(data) {
  return request.post('/fact/car-usage', data)
}

export function batchSaveCarUsages(data) {
  return request.post('/fact/car-usage/batch', data)
}

export function deleteCarUsage(id) {
  return request.delete(`/fact/car-usage/${id}`)
}
