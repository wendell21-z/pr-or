import request from './request'

// Solve APIs
export function startSolve(data) {
  return request.post('/solve/start', data)
}

export function isRunning() {
  return request.get('/solve/is-running')
}



export function getSolveStatus(lineId) {
  return request.get('/solve/status', { params: { linId: lineId } })
}

export function getAllSolveResults() {
  return request.get('/solve/result/all')
}

export function getLatestSolveResult() {
  return request.get('/solve/result/latest')
}

export function getSolveResultByWeek(lineId, begin, end) {
  return request.get('/solution/solve-result', { params: { lineId, begin, end } })
}
