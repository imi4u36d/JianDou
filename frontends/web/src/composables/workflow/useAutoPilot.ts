/**
 * 自动执行（AutoPilot）组合式逻辑。
 * 管理工作流自动执行的生命周期：启动、暂停、恢复、终止，
 * 并在自动执行状态下启动高频轮询以刷新状态。
 */
import { ref, computed, onUnmounted } from 'vue'
import { startAutoPilot, pauseAutoPilot, resumeAutoPilot, terminateAutoPilot } from '@/api/workflows'
import { messageApi } from '@/composables/useMessage'

interface StatusLogEntry {
  id: number
  stage: string
  message: string
  stateKey: string
  timestamp: string
}

let logCounter = 0

export function useAutoPilot(getWorkflowId: () => string) {
  // State
  const autoPilotState = ref<string>('idle')
  const nextStage = ref<string>('')
  const currentTask = ref<string>('')
  const errorMessage = ref<string>('')
  const busy = ref(false)
  const statusLog = ref<StatusLogEntry[]>([])
  let pollTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * 向状态日志追加一条新条目，替换旧条目以保持最多 20 条。
   * @param stage 显示的标签文本（中文）
   * @param message 描述文本
   * @param stateKey 用于 CSS 样式的状态键（英文 state 值）
   */
  function pushStatusLog(stage: string, message: string, stateKey: string = '') {
    const entry: StatusLogEntry = {
      id: ++logCounter,
      stage,
      message,
      stateKey,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }
    statusLog.value = [...statusLog.value.slice(-19), entry]
  }

  function getCurrentWorkflowId(): string {
    return getWorkflowId()
  }

  // Actions
  async function startAutoPilotAction() {
    busy.value = true
    try {
      await startAutoPilot(getCurrentWorkflowId())
      autoPilotState.value = 'queued'
      messageApi.success('自动执行已启动')
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : '启动失败')
    } finally {
      busy.value = false
    }
  }

  async function pauseAutoPilotAction() {
    busy.value = true
    try {
      await pauseAutoPilot(getCurrentWorkflowId())
      messageApi.success('已暂停')
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : '暂停失败')
    } finally {
      busy.value = false
    }
  }

  async function resumeAutoPilotAction() {
    busy.value = true
    try {
      await resumeAutoPilot(getCurrentWorkflowId())
      autoPilotState.value = 'queued'
      messageApi.success('已恢复自动执行')
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : '恢复失败')
    } finally {
      busy.value = false
    }
  }

  async function terminateAutoPilotAction() {
    busy.value = true
    try {
      await terminateAutoPilot(getCurrentWorkflowId())
      messageApi.success('已切换为手动模式')
    } catch (e) {
      messageApi.error(e instanceof Error ? e.message : '终止失败')
    } finally {
      busy.value = false
    }
  }

  /**
   * 启动轮询：以 2 秒间隔刷新工作流详情。
   */
  function startPolling(refreshWorkflow: () => Promise<void>) {
    async function tick() {
      await refreshWorkflow()
      pollTimer = setTimeout(tick, 2000)
    }
    tick()
  }

  /**
   * 停止轮询。
   */
  function stopPolling() {
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  const isRunning = computed(() => autoPilotState.value === 'running')
  const isPaused = computed(() => autoPilotState.value === 'paused')
  const isFailed = computed(() => autoPilotState.value === 'failed')
  const isQueued = computed(() => autoPilotState.value === 'queued')
  const isActive = computed(() => autoPilotState.value === 'running' || autoPilotState.value === 'queued')

  onUnmounted(() => {
    stopPolling()
  })

  return {
    autoPilotState,
    nextStage,
    currentTask,
    errorMessage,
    busy,
    statusLog,
    isRunning,
    isPaused,
    isFailed,
    isQueued,
    isActive,
    startAutoPilot: startAutoPilotAction,
    pauseAutoPilot: pauseAutoPilotAction,
    resumeAutoPilot: resumeAutoPilotAction,
    terminateAutoPilot: terminateAutoPilotAction,
    startPolling,
    stopPolling,
    pushStatusLog,
  }
}
