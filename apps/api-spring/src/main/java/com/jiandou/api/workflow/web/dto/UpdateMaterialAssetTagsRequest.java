package com.jiandou.api.workflow.web.dto;

import java.util.List;

public record UpdateMaterialAssetTagsRequest(
    List<String> tags
) {}
