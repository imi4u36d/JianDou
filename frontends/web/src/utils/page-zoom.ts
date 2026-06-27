type EventTargetLike = Pick<EventTarget, "addEventListener" | "removeEventListener">;

const eventOptions: AddEventListenerOptions = { capture: true, passive: false };
const zoomKeys = new Set(["+", "-", "=", "0", "add", "subtract"]);

function isZoomKeydown(event: KeyboardEvent): boolean {
  if (!event.ctrlKey && !event.metaKey) {
    return false;
  }

  return zoomKeys.has(event.key.toLowerCase());
}

function preventZoomKeydown(event: KeyboardEvent): void {
  if (isZoomKeydown(event)) {
    event.preventDefault();
  }
}

function preventZoomWheel(event: WheelEvent): void {
  if (event.ctrlKey || event.metaKey) {
    event.preventDefault();
  }
}

function preventGestureZoom(event: Event): void {
  event.preventDefault();
}

function preventMultiTouchZoom(event: TouchEvent): void {
  if (event.touches.length > 1) {
    event.preventDefault();
  }
}

export function installPageZoomGuard(
  target: EventTargetLike = window,
  gestureTarget: EventTargetLike = document,
): () => void {
  target.addEventListener("keydown", preventZoomKeydown as EventListener, eventOptions);
  target.addEventListener("wheel", preventZoomWheel as EventListener, eventOptions);
  gestureTarget.addEventListener("touchmove", preventMultiTouchZoom as EventListener, eventOptions);
  gestureTarget.addEventListener("gesturestart", preventGestureZoom, eventOptions);
  gestureTarget.addEventListener("gesturechange", preventGestureZoom, eventOptions);
  gestureTarget.addEventListener("gestureend", preventGestureZoom, eventOptions);

  return () => {
    target.removeEventListener("keydown", preventZoomKeydown as EventListener, eventOptions);
    target.removeEventListener("wheel", preventZoomWheel as EventListener, eventOptions);
    gestureTarget.removeEventListener("touchmove", preventMultiTouchZoom as EventListener, eventOptions);
    gestureTarget.removeEventListener("gesturestart", preventGestureZoom, eventOptions);
    gestureTarget.removeEventListener("gesturechange", preventGestureZoom, eventOptions);
    gestureTarget.removeEventListener("gestureend", preventGestureZoom, eventOptions);
  };
}
