import { ref, computed } from 'vue'
import { getThreadId } from '../services/api'

const stats = ref({
  researchCount: 0,
  reportCount: 0,
  totalTime: 0,
  sourceCount: 0,
})

const avgTime = computed(() => {
  if (stats.value.researchCount === 0) return 0
  return Math.round(stats.value.totalTime / stats.value.researchCount / 60)
})

let _currentThreadId = null

function load(threadId) {
  if (threadId === _currentThreadId) return
  _currentThreadId = threadId
  const storageKey = `iris_stats_${threadId}`
  const saved = localStorage.getItem(storageKey)
  if (saved) {
    stats.value = JSON.parse(saved)
  } else {
    stats.value = {
      researchCount: 5,
      reportCount: 3,
      totalTime: 720,
      sourceCount: 47,
    }
    localStorage.setItem(storageKey, JSON.stringify(stats.value))
  }
}

function save() {
  if (!_currentThreadId) return
  localStorage.setItem(`iris_stats_${_currentThreadId}`, JSON.stringify(stats.value))
}

export function useStats() {
  const threadId = getThreadId()
  load(threadId)

  const recordResearch = (durationSeconds, sourceCount) => {
    stats.value.researchCount++
    stats.value.reportCount++
    stats.value.totalTime += durationSeconds
    stats.value.sourceCount += sourceCount
    save()
  }

  return { stats, avgTime, recordResearch }
}
