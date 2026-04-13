import request from './request'

// Task APIs
export function addPinnedTask(data) {
  return request.post('/solution/task', data)
}

export function updateTask(data) {
  return request.put('/solution/task', data)
}

export function deleteTask(id) {
  return request.delete('/solution/task', { params: { id } })
}

export function swapTasks(task1Id, task2Id) {
  return request.get('/solution/task/swap', { params: { task1Id, task2Id } })
}

// Die Memo APIs
export function getMemos() {
  return request.get('/solution/die-memo')
}

export function saveMemo(data) {
  return request.post('/solution/die-memo', data)
}

export function deleteMemo(memoId) {
  return request.delete('/solution/die-memo', { params: { memoId } })
}
