package com.jiandou.api.workflow.web;

import com.jiandou.api.config.ApiPathConstants;
import com.jiandou.api.workflow.application.WorkflowApplicationService;
import com.jiandou.api.workflow.web.dto.ReuseMaterialRequest;
import com.jiandou.api.workflow.web.dto.UpdateMaterialAssetRatingRequest;
import com.jiandou.api.workflow.web.dto.UpdateMaterialAssetTagsRequest;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping(ApiPathConstants.MATERIAL_ASSETS)
public class MaterialAssetController {

    private final WorkflowApplicationService workflowService;

    public MaterialAssetController(WorkflowApplicationService workflowService) {
        this.workflowService = workflowService;
    }

    @GetMapping
    public List<Map<String, Object>> listMaterialAssets(
        @RequestParam(value = "q", required = false) String q,
        @RequestParam(value = "type", required = false) String type,
        @RequestParam(value = "tag", required = false) String tag,
        @RequestParam(value = "minRating", required = false) Integer minRating,
        @RequestParam(value = "model", required = false) String model,
        @RequestParam(value = "aspectRatio", required = false) String aspectRatio,
        @RequestParam(value = "clipIndex", required = false) Integer clipIndex
    ) {
        return workflowService.listMaterialAssets(q, type, tag, minRating, model, aspectRatio, clipIndex);
    }

    @GetMapping("/{assetId}")
    public Map<String, Object> getMaterialAsset(@PathVariable String assetId) {
        return workflowService.getMaterialAsset(assetId);
    }

    @PatchMapping("/{assetId}/rating")
    public Map<String, Object> rateMaterialAsset(@PathVariable String assetId, @RequestBody UpdateMaterialAssetRatingRequest request) {
        return workflowService.rateMaterialAsset(assetId, request);
    }

    @PatchMapping("/{assetId}/tags")
    public Map<String, Object> updateMaterialAssetTags(@PathVariable String assetId, @RequestBody UpdateMaterialAssetTagsRequest request) {
        return workflowService.updateMaterialAssetTags(assetId, request);
    }

    @PostMapping("/{assetId}/reuse")
    public Map<String, Object> reuseMaterialAsset(@PathVariable String assetId, @RequestBody(required = false) ReuseMaterialRequest request) {
        return workflowService.reuseMaterialAsset(assetId, request == null ? new ReuseMaterialRequest("clone") : request);
    }
}
