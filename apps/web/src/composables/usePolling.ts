import { onUnmounted, ref } from "vue";

export function usePolling(callback: () => Promise<void> | void, delayMs: number) {
  const active = ref(false);
  const running = ref(false);
  const timer = ref<number | null>(null);

  const stop = () => {
    active.value = false;
    if (timer.value !== null) {
      window.clearTimeout(timer.value);
      timer.value = null;
    }
  };

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
