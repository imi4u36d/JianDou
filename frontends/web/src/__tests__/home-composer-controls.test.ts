import { nextTick, reactive, ref } from "vue";
import { describe, expect, it, vi } from "vitest";
import { useHomeComposerControls } from "@/composables/home/useHomeComposerControls";
import type { ModeOption, ModeValue, WorkbenchForm } from "@/composables/home/useGenerationForm";

function setup(authenticated = true) {
  const mode = ref<ModeValue>("image");
  const prompt = ref("一只猫");
  const references = ref([{ id: "ref", label: "图片1", fileName: "ref.png", fileUrl: "ref.png" }]);
  const expanded = ref(true);
  const form = reactive({
    aspectRatio: "16:9",
    textAnalysisModel: "text-model",
    imageModel: "image-model",
    videoModel: "video-model",
    videoSize: "1280*720",
  }) as WorkbenchForm;
  const renderPromptEditor = vi.fn();
  const saveAspectRatio = vi.fn(async () => undefined);
  const openCredits = vi.fn();
  const modes: Record<ModeValue, ModeOption> = {
    image: { value: "image", kind: "image", label: "图片", description: "", iconName: "image" },
    video: { value: "video", kind: "video", label: "视频", description: "", iconName: "video" },
    character_sheet: { value: "character_sheet", kind: "image", label: "角色", description: "", iconName: "character" },
  };
  const controls = useHomeComposerControls({
    selectedMode: () => modes[mode.value],
    selectedModeValue: () => mode.value,
    setSelectedModeValue: (value) => { mode.value = value; },
    form: () => form,
    prompt: () => prompt.value,
    setPrompt: (value) => { prompt.value = value; },
    imageOutputCount: () => 2,
    selectedImageModel: () => ({ supportsSeed: true }) as never,
    seedMode: () => "manual",
    manualSeed: () => 42,
    autoSeed: () => 7,
    referenceImages: () => references.value,
    clearReferenceImages: () => { references.value = []; },
    collapseReferences: () => { expanded.value = false; },
    authenticated: () => authenticated,
    credits: () => ({ balance: 10 }) as never,
    saveAspectRatio,
    authorizeCredits: async () => authenticated,
    openCredits,
    renderPromptEditor,
    focusPromptEditorToEnd: vi.fn(),
  });
  return { controls, mode, prompt, references, expanded, form, renderPromptEditor, saveAspectRatio, openCredits };
}

describe("home composer controls", () => {
  it("owns menu, mode, ratio and submission snapshot state", () => {
    const { controls, mode, form, saveAspectRatio } = setup();

    controls.toggleMenu("mode");
    expect(controls.activeMenu.value).toBe("mode");
    controls.selectMode("video");
    expect(mode.value).toBe("video");
    expect(controls.statusText.value).toContain("阶段工作流");
    controls.selectRatio("9:16");
    expect(form.aspectRatio).toBe("9:16");
    expect(saveAspectRatio).toHaveBeenCalledWith("9:16");
    expect(controls.submissionSnapshot()).toMatchObject({
      mode: "video",
      prompt: "一只猫",
      outputCount: 2,
      manualSeed: 42,
      referenceImageUrls: ["ref.png"],
    });
  });

  it("applies templates, resets composer state, and gates credit details", async () => {
    const { controls, prompt, references, expanded, renderPromptEditor, openCredits } = setup();

    controls.applyPromptTemplate({ id: "ink", title: "水墨", prompt: "[主体]，水墨" });
    await nextTick();
    expect(controls.selectedPromptTemplate.value?.id).toBe("ink");
    expect(renderPromptEditor).toHaveBeenCalledWith("一只猫");
    await controls.openCreditDialog();
    expect(openCredits).toHaveBeenCalledOnce();

    controls.resetComposerAfterSuccessfulSubmit();
    await nextTick();
    expect(prompt.value).toBe("");
    expect(references.value).toEqual([]);
    expect(expanded.value).toBe(false);
  });
});
