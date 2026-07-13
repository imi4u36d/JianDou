import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

interface ImageTaskListViewportOptions {
  itemCount: () => number;
  hasMore: () => boolean;
  loading: () => boolean;
  loadingMore: () => boolean;
  emitLoadMore: () => void;
  emitPageSizeChange: (size: number) => void;
}

export function calculateImageTaskPageSize(
  availableHeight: number,
  itemHeight: number,
  itemGap: number,
): number {
  const rowHeight = Math.max(1, itemHeight + itemGap);
  return Math.max(4, Math.floor(Math.max(0, availableHeight) / rowHeight));
}

export function useImageTaskListViewport(options: ImageTaskListViewportOptions) {
  const panelRef = ref<HTMLElement | null>(null);
  const listRef = ref<HTMLElement | null>(null);
  const loadMoreSentinelRef = ref<HTMLElement | null>(null);
  let resizeObserver: ResizeObserver | null = null;
  let intersectionObserver: IntersectionObserver | null = null;
  let lastEmittedPageSize = 0;

  function emitViewportPageSize() {
    const panel = panelRef.value;
    if (!panel) return;
    const list = listRef.value;
    const styles = window.getComputedStyle(panel);
    const rowGap = Number.parseFloat(styles.rowGap || styles.gap || "12") || 12;
    const searchHeight = panel.querySelector<HTMLElement>(".image-task-search-field")?.offsetHeight ?? 40;
    const filterHeight = panel.querySelector<HTMLElement>(".image-task-filter-strip")?.offsetHeight ?? 34;
    const listItemHeight = panel.querySelector<HTMLElement>(".image-task-list-item")?.offsetHeight ?? 76;
    const listGap = Number.parseFloat(window.getComputedStyle(list ?? panel).rowGap || "8") || 8;
    const availableHeight = list?.clientHeight ?? panel.clientHeight - searchHeight - filterHeight - rowGap * 2;
    const nextPageSize = calculateImageTaskPageSize(availableHeight, listItemHeight, listGap);
    if (Number.isFinite(nextPageSize) && nextPageSize !== lastEmittedPageSize) {
      lastEmittedPageSize = nextPageSize;
      options.emitPageSizeChange(nextPageSize);
    }
  }

  function handleScroll(event: Event) {
    const target = event.currentTarget;
    if (!(target instanceof HTMLElement)) return;
    const distanceToBottom = target.scrollHeight - target.scrollTop - target.clientHeight;
    if (distanceToBottom <= 96) options.emitLoadMore();
  }

  function observeLoadMoreSentinel() {
    intersectionObserver?.disconnect();
    intersectionObserver = null;
    const panel = listRef.value;
    const sentinel = loadMoreSentinelRef.value;
    if (!panel || !sentinel || typeof IntersectionObserver === "undefined") return;
    intersectionObserver = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting && options.hasMore() && !options.loading() && !options.loadingMore()) {
          options.emitLoadMore();
        }
      },
      { root: panel, rootMargin: "120px 0px", threshold: 0 },
    );
    intersectionObserver.observe(sentinel);
  }

  onMounted(async () => {
    await nextTick();
    emitViewportPageSize();
    observeLoadMoreSentinel();
    if (panelRef.value && typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        emitViewportPageSize();
        observeLoadMoreSentinel();
      });
      resizeObserver.observe(panelRef.value);
    }
  });

  watch(
    () => [options.itemCount(), options.hasMore(), options.loading(), options.loadingMore()],
    async () => {
      await nextTick();
      emitViewportPageSize();
      observeLoadMoreSentinel();
    },
    { flush: "post" },
  );

  onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    intersectionObserver?.disconnect();
    resizeObserver = null;
    intersectionObserver = null;
  });

  return { panelRef, listRef, loadMoreSentinelRef, handleScroll };
}
