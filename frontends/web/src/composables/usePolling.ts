/**
 * use轮询组合式逻辑。
 */
import { onUnmounted, ref } from "vue";

/**
 * 处理use轮询。
 * @param callback 要执行的回调
 * @param delayMs 轮询间隔（毫秒）
 */
export function usePolling(callback: () => Promise<void> | void, delayMs: number) {
  const active = ref(false);
  const running = ref(false);
  const timer = ref<number | null>(null);

  /**
   * 停止stop。
   */
  const stop = () => {
    active.value = false;
    if (timer.value !== null) {
      window.clearTimeout(timer.value);
      timer.value = null;
    }
  };

  /**
   * 处理调度。
   */
  const schedule = () => {
    if (!active.value) {
      return;
    }

    timer.value = window.setTimeout(async () => {
      timer.value = null;
      if (!active.value || running.value) {
        return;
      }

      running.value = true;
      try {
        await callback();
      } finally {
        running.value = false;
        if (active.value) {
          schedule();
        }
      }
    }, delayMs);
  };

  const start = async (immediate = true) => {
    stop();
    active.value = true;

    if (!immediate) {
      schedule();
      return;
    }

    running.value = true;
    try {
      await callback();
    } finally {
      running.value = false;
      if (active.value) {
        schedule();
      }
    }
  };

  onUnmounted(stop);

  return {
    active,
    running,
    start,
    stop
  };
}
