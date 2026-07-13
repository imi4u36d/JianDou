export const REFERENCE_PREVIEW_WIDTH = 68;
export const REFERENCE_PREVIEW_HEIGHT = 98;
export const REFERENCE_COLLAPSED_WIDTH = 58;
export const REFERENCE_COLLAPSED_HEIGHT = 84;
export const REFERENCE_EXPANDED_MAX_TILT_DEG = 30;
export const REFERENCE_EXPANDED_GAP = 8;
export const REFERENCE_EXPANDED_BOTTOM = 8;
export const REFERENCE_ADD_CARD_OFFSET = 86;

export function referencePreviewRotation(index: number, expanded: boolean) {
  const rotations = expanded ? [-9, 6, -7, 8, -5, 7, -8, 5, -6, 9, -4, 6] : [-7, 4, -5, 6, -4, 5];
  return rotations[index % rotations.length];
}

export function referenceExpandedStep() {
  const radians = (REFERENCE_EXPANDED_MAX_TILT_DEG * Math.PI) / 180;
  const projectedWidth =
    REFERENCE_PREVIEW_WIDTH * Math.cos(radians) + REFERENCE_PREVIEW_HEIGHT * Math.sin(radians);
  return Math.ceil(projectedWidth + REFERENCE_EXPANDED_GAP);
}

export function referenceRotationBottomDelta(rotateDeg: number) {
  return Math.sin((Math.abs(rotateDeg) * Math.PI) / 180) * (REFERENCE_PREVIEW_WIDTH / 2);
}

export function referenceExpandedBottom(rotateDeg: number) {
  const firstDelta = referenceRotationBottomDelta(referencePreviewRotation(0, true));
  return `${REFERENCE_EXPANDED_BOTTOM - firstDelta + referenceRotationBottomDelta(rotateDeg)}px`;
}

export function referenceUploadSceneStyle(imageCount: number, expanded: boolean) {
  if (imageCount <= 1) {
    return expanded
      ? {
          width: `${REFERENCE_PREVIEW_WIDTH + REFERENCE_ADD_CARD_OFFSET}px`,
          height: `${REFERENCE_PREVIEW_HEIGHT}px`,
        }
      : undefined;
  }
  if (!expanded) return undefined;
  return {
    width: `${imageCount * referenceExpandedStep() + REFERENCE_PREVIEW_WIDTH}px`,
    height: "112px",
  };
}

export function referencePreviewImageStyle(index: number, total: number, expanded: boolean) {
  if (total <= 1) {
    const rotate = -8;
    return {
      left: "0px",
      top: "0px",
      bottom: "auto",
      width: `${REFERENCE_PREVIEW_WIDTH}px`,
      height: `${REFERENCE_PREVIEW_HEIGHT}px`,
      opacity: "1",
      zIndex: "1",
      "--preview-rotate": `${rotate}deg`,
      "--preview-remove-rotate": `${-rotate}deg`,
      transformOrigin: "center bottom",
      transform: `rotate(${rotate}deg)`,
    };
  }
  if (expanded) {
    const rotate = referencePreviewRotation(index, true);
    return {
      left: `${index * referenceExpandedStep()}px`,
      top: "auto",
      bottom: referenceExpandedBottom(rotate),
      width: `${REFERENCE_PREVIEW_WIDTH}px`,
      height: `${REFERENCE_PREVIEW_HEIGHT}px`,
      opacity: "1",
      zIndex: String(index + 1),
      "--preview-rotate": `${rotate}deg`,
      "--preview-remove-rotate": `${-rotate}deg`,
      transformOrigin: "center bottom",
      transform: `rotate(${rotate}deg)`,
    };
  }
  const visibleIndex = Math.min(index, 4);
  const rotate = referencePreviewRotation(visibleIndex, false);
  return {
    left: `${-6 + visibleIndex * 8}px`,
    top: `${4 - Math.min(visibleIndex, 2) * 2}px`,
    bottom: "auto",
    width: `${REFERENCE_COLLAPSED_WIDTH}px`,
    height: `${REFERENCE_COLLAPSED_HEIGHT}px`,
    opacity: index < 4 ? "0.96" : "0",
    zIndex: String(index + 1),
    "--preview-rotate": `${rotate}deg`,
    "--preview-remove-rotate": `${-rotate}deg`,
    transformOrigin: "center bottom",
    transform: `rotate(${rotate}deg)`,
  };
}

export function referenceAddCardStyle(imageCount: number, expanded: boolean) {
  if (imageCount <= 1) {
    return expanded
      ? { left: `${REFERENCE_ADD_CARD_OFFSET}px`, top: "0px", bottom: "auto" }
      : undefined;
  }
  if (!expanded) return undefined;
  const firstDelta = referenceRotationBottomDelta(referencePreviewRotation(0, true));
  return {
    left: `${imageCount * referenceExpandedStep()}px`,
    top: "auto",
    bottom: `${REFERENCE_EXPANDED_BOTTOM - firstDelta}px`,
  };
}
