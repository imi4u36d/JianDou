ALTER TABLE `biz_task_results`
  MODIFY COLUMN `preview_path` TEXT NOT NULL COMMENT '预览路径',
  MODIFY COLUMN `download_path` TEXT NOT NULL COMMENT '下载路径',
  MODIFY COLUMN `remote_url` TEXT NOT NULL COMMENT '远端结果地址';

SET @owner_user_id_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'owner_user_id'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `owner_user_id` bigint unsigned DEFAULT NULL COMMENT ''归属用户ID'' AFTER `material_asset_id`'
  )
);
PREPARE stmt FROM @owner_user_id_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @workflow_id_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'workflow_id'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `workflow_id` varchar(64) NOT NULL DEFAULT '''' COMMENT ''关联工作流ID'' AFTER `task_id`'
  )
);
PREPARE stmt FROM @workflow_id_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @stage_type_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'stage_type'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `stage_type` varchar(32) NOT NULL DEFAULT '''' COMMENT ''阶段类型'' AFTER `asset_role`'
  )
);
PREPARE stmt FROM @stage_type_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @clip_index_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'clip_index'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `clip_index` int NOT NULL DEFAULT ''0'' COMMENT ''镜头序号'' AFTER `stage_type`'
  )
);
PREPARE stmt FROM @clip_index_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @version_no_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'version_no'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `version_no` int NOT NULL DEFAULT ''0'' COMMENT ''版本号'' AFTER `clip_index`'
  )
);
PREPARE stmt FROM @version_no_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @selected_for_next_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'selected_for_next'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `selected_for_next` tinyint(1) NOT NULL DEFAULT ''0'' COMMENT ''是否被选为继续依据'' AFTER `version_no`'
  )
);
PREPARE stmt FROM @selected_for_next_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @user_rating_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'user_rating'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `user_rating` int DEFAULT NULL COMMENT ''用户评分'' AFTER `selected_for_next`'
  )
);
PREPARE stmt FROM @user_rating_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @rating_note_sql = (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'biz_material_assets'
        AND column_name = 'rating_note'
    ),
    'SELECT 1',
    'ALTER TABLE `biz_material_assets` ADD COLUMN `rating_note` varchar(1000) NOT NULL DEFAULT '''' COMMENT ''评分备注'' AFTER `user_rating`'
  )
);
PREPARE stmt FROM @rating_note_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE `biz_material_assets`
  MODIFY COLUMN `local_storage_path` TEXT NOT NULL COMMENT '本地相对路径',
  MODIFY COLUMN `local_file_path` TEXT NOT NULL COMMENT '本地绝对路径',
  MODIFY COLUMN `public_url` TEXT NOT NULL COMMENT '对外访问 URL',
  MODIFY COLUMN `third_party_url` TEXT NOT NULL COMMENT '第三方 URL',
  MODIFY COLUMN `remote_url` TEXT NOT NULL COMMENT '远端 URL';
