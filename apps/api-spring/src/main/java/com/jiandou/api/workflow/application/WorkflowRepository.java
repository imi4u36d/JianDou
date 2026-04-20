package com.jiandou.api.workflow.application;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetEntity;
import com.jiandou.api.task.infrastructure.mybatis.MaterialAssetMapper;
import com.jiandou.api.workflow.infrastructure.mybatis.MaterialAssetTagEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.MaterialAssetTagMapper;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageVersionMapper;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowEntity;
import com.jiandou.api.workflow.infrastructure.mybatis.StageWorkflowMapper;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.springframework.stereotype.Repository;

@Repository
public class WorkflowRepository {

    private final SqlSessionFactory sqlSessionFactory;

    public WorkflowRepository(SqlSessionFactory sqlSessionFactory) {
        this.sqlSessionFactory = sqlSessionFactory;
    }

    public void saveWorkflow(StageWorkflowEntity entity) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            StageWorkflowMapper mapper = session.getMapper(StageWorkflowMapper.class);
            StageWorkflowEntity existing = mapper.selectById(entity.getWorkflowId());
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.updateById(entity);
            }
        }
    }

    public StageWorkflowEntity findWorkflow(String workflowId, Long ownerUserId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(StageWorkflowMapper.class).selectOne(
                Wrappers.<StageWorkflowEntity>lambdaQuery()
                    .eq(StageWorkflowEntity::getWorkflowId, workflowId)
                    .eq(ownerUserId != null, StageWorkflowEntity::getOwnerUserId, ownerUserId)
                    .eq(StageWorkflowEntity::getIsDeleted, 0)
                    .last("LIMIT 1")
            );
        }
    }

    public List<StageWorkflowEntity> listWorkflows(Long ownerUserId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(StageWorkflowMapper.class).selectList(
                Wrappers.<StageWorkflowEntity>lambdaQuery()
                    .eq(ownerUserId != null, StageWorkflowEntity::getOwnerUserId, ownerUserId)
                    .eq(StageWorkflowEntity::getIsDeleted, 0)
                    .orderByDesc(StageWorkflowEntity::getUpdateTime)
            );
        }
    }

    public void saveStageVersion(StageVersionEntity entity) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            StageVersionMapper mapper = session.getMapper(StageVersionMapper.class);
            StageVersionEntity existing = mapper.selectById(entity.getStageVersionId());
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.updateById(entity);
            }
        }
    }

    public StageVersionEntity findStageVersion(String workflowId, String versionId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(StageVersionMapper.class).selectOne(
                Wrappers.<StageVersionEntity>lambdaQuery()
                    .eq(StageVersionEntity::getWorkflowId, workflowId)
                    .eq(StageVersionEntity::getStageVersionId, versionId)
                    .eq(StageVersionEntity::getIsDeleted, 0)
                    .last("LIMIT 1")
            );
        }
    }

    public StageVersionEntity findStageVersionByMaterialAssetId(String materialAssetId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(StageVersionMapper.class).selectOne(
                Wrappers.<StageVersionEntity>lambdaQuery()
                    .eq(StageVersionEntity::getMaterialAssetId, materialAssetId)
                    .eq(StageVersionEntity::getIsDeleted, 0)
                    .orderByDesc(StageVersionEntity::getCreateTime)
                    .last("LIMIT 1")
            );
        }
    }

    public List<StageVersionEntity> listStageVersions(String workflowId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(StageVersionMapper.class).selectList(
                Wrappers.<StageVersionEntity>lambdaQuery()
                    .eq(StageVersionEntity::getWorkflowId, workflowId)
                    .eq(StageVersionEntity::getIsDeleted, 0)
                    .orderByAsc(StageVersionEntity::getStageType)
                    .orderByAsc(StageVersionEntity::getClipIndex)
                    .orderByDesc(StageVersionEntity::getVersionNo)
            );
        }
    }

    public int nextStageVersionNo(String workflowId, String stageType, int clipIndex) {
        List<StageVersionEntity> versions = listStageVersions(workflowId);
        return versions.stream()
            .filter(item -> stageType.equals(item.getStageType()) && clipIndex == defaultInt(item.getClipIndex()))
            .map(StageVersionEntity::getVersionNo)
            .filter(item -> item != null && item > 0)
            .max(Integer::compareTo)
            .orElse(0) + 1;
    }

    public void markSelectedStageVersion(String workflowId, String stageType, int clipIndex, String selectedVersionId) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            StageVersionMapper mapper = session.getMapper(StageVersionMapper.class);
            List<StageVersionEntity> versions = mapper.selectList(
                Wrappers.<StageVersionEntity>lambdaQuery()
                    .eq(StageVersionEntity::getWorkflowId, workflowId)
                    .eq(StageVersionEntity::getStageType, stageType)
                    .eq(StageVersionEntity::getClipIndex, clipIndex)
                    .eq(StageVersionEntity::getIsDeleted, 0)
            );
            for (StageVersionEntity item : versions) {
                item.setSelected(item.getStageVersionId().equals(selectedVersionId) ? 1 : 0);
                mapper.updateById(item);
            }
        }
    }

    public void clearSelectedStageVersions(String workflowId, String stageType, Integer clipIndex) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            StageVersionMapper mapper = session.getMapper(StageVersionMapper.class);
            var query = Wrappers.<StageVersionEntity>lambdaQuery()
                .eq(StageVersionEntity::getWorkflowId, workflowId)
                .eq(StageVersionEntity::getStageType, stageType)
                .eq(StageVersionEntity::getIsDeleted, 0);
            if (clipIndex != null) {
                query.eq(StageVersionEntity::getClipIndex, clipIndex);
            }
            List<StageVersionEntity> versions = mapper.selectList(query);
            for (StageVersionEntity item : versions) {
                item.setSelected(0);
                mapper.updateById(item);
            }
        }
    }

    public void saveMaterialAsset(MaterialAssetEntity entity) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            MaterialAssetMapper mapper = session.getMapper(MaterialAssetMapper.class);
            MaterialAssetEntity existing = mapper.selectById(entity.getMaterialAssetId());
            if (existing == null) {
                mapper.insert(entity);
            } else {
                mapper.updateById(entity);
            }
        }
    }

    public MaterialAssetEntity findMaterialAsset(String assetId, Long ownerUserId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(MaterialAssetMapper.class).selectOne(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(MaterialAssetEntity::getMaterialAssetId, assetId)
                    .eq(ownerUserId != null, MaterialAssetEntity::getOwnerUserId, ownerUserId)
                    .eq(MaterialAssetEntity::getIsDeleted, 0)
                    .last("LIMIT 1")
            );
        }
    }

    public List<MaterialAssetEntity> listMaterialAssets(Long ownerUserId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(MaterialAssetMapper.class).selectList(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .eq(ownerUserId != null, MaterialAssetEntity::getOwnerUserId, ownerUserId)
                    .eq(MaterialAssetEntity::getIsDeleted, 0)
                    .orderByDesc(MaterialAssetEntity::getCreateTime)
            );
        }
    }

    public void saveMaterialAssetTags(String materialAssetId, List<MaterialAssetTagEntity> tags) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            MaterialAssetTagMapper mapper = session.getMapper(MaterialAssetTagMapper.class);
            List<MaterialAssetTagEntity> existing = mapper.selectList(
                Wrappers.<MaterialAssetTagEntity>lambdaQuery()
                    .eq(MaterialAssetTagEntity::getMaterialAssetId, materialAssetId)
                    .eq(MaterialAssetTagEntity::getIsDeleted, 0)
            );
            for (MaterialAssetTagEntity item : existing) {
                item.setIsDeleted(1);
                mapper.updateById(item);
            }
            for (MaterialAssetTagEntity item : tags) {
                mapper.insert(item);
            }
        }
    }

    public Map<String, List<MaterialAssetTagEntity>> listTagsByAssetIds(Collection<String> assetIds) {
        if (assetIds == null || assetIds.isEmpty()) {
            return Map.of();
        }
        try (SqlSession session = sqlSessionFactory.openSession()) {
            List<MaterialAssetTagEntity> tags = session.getMapper(MaterialAssetTagMapper.class).selectList(
                Wrappers.<MaterialAssetTagEntity>lambdaQuery()
                    .in(MaterialAssetTagEntity::getMaterialAssetId, assetIds)
                    .eq(MaterialAssetTagEntity::getIsDeleted, 0)
                    .orderByAsc(MaterialAssetTagEntity::getTagType)
                    .orderByAsc(MaterialAssetTagEntity::getTagKey)
                    .orderByAsc(MaterialAssetTagEntity::getTagValue)
            );
            return tags.stream().collect(Collectors.groupingBy(MaterialAssetTagEntity::getMaterialAssetId, LinkedHashMap::new, Collectors.toList()));
        }
    }

    public List<MaterialAssetTagEntity> listTags(String materialAssetId) {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(MaterialAssetTagMapper.class).selectList(
                Wrappers.<MaterialAssetTagEntity>lambdaQuery()
                    .eq(MaterialAssetTagEntity::getMaterialAssetId, materialAssetId)
                    .eq(MaterialAssetTagEntity::getIsDeleted, 0)
                    .orderByAsc(MaterialAssetTagEntity::getTagType)
                    .orderByAsc(MaterialAssetTagEntity::getTagKey)
                    .orderByAsc(MaterialAssetTagEntity::getTagValue)
            );
        }
    }

    public Map<String, MaterialAssetEntity> findMaterialAssetsByIds(Set<String> assetIds, Long ownerUserId) {
        if (assetIds == null || assetIds.isEmpty()) {
            return Map.of();
        }
        try (SqlSession session = sqlSessionFactory.openSession()) {
            List<MaterialAssetEntity> entities = session.getMapper(MaterialAssetMapper.class).selectList(
                Wrappers.<MaterialAssetEntity>lambdaQuery()
                    .in(MaterialAssetEntity::getMaterialAssetId, assetIds)
                    .eq(ownerUserId != null, MaterialAssetEntity::getOwnerUserId, ownerUserId)
                    .eq(MaterialAssetEntity::getIsDeleted, 0)
            );
            Map<String, MaterialAssetEntity> result = new LinkedHashMap<>();
            for (MaterialAssetEntity item : entities) {
                result.put(item.getMaterialAssetId(), item);
            }
            return result;
        }
    }

    public OffsetDateTime now() {
        return OffsetDateTime.now();
    }

    private int defaultInt(Integer value) {
        return value == null ? 0 : value;
    }
}
