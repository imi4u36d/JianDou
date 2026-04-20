package com.jiandou.api.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import javax.sql.DataSource;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 数据库SchemaInitializer。
 */
@Configuration
public class DatabaseSchemaInitializer {

    /**
     * 处理数据库SchemaRunner。
     * @param dataSource data来源值
     * @return 处理结果
     */
    @Bean("databaseSchemaReady")
    public InitializingBean databaseSchemaRunner(DataSource dataSource) {
        return () -> initializeSchema(dataSource);
    }

    /**
     * 处理initializeSchema。
     * @param dataSource data来源值
     */
    private void initializeSchema(DataSource dataSource) throws SQLException, IOException {
        String script;
        try (InputStream inputStream = Thread.currentThread().getContextClassLoader().getResourceAsStream("schema.sql")) {
            if (inputStream == null) {
                return;
            }
            script = new String(inputStream.readAllBytes(), StandardCharsets.UTF_8);
        }
        try (Connection connection = dataSource.getConnection(); Statement statement = connection.createStatement()) {
            for (String rawSql : script.split(";")) {
                String sql = rawSql.trim();
                if (!sql.isEmpty()) {
                    try {
                        statement.execute(sql);
                    } catch (SQLException ex) {
                        if (!isIgnorableSchemaError(ex)) {
                            throw ex;
                        }
                    }
                }
            }
            ensureCompatibleUrlColumns(connection);
        }
    }

    /**
     * 检查是否IgnorableSchemaError。
     * @param ex ex值
     * @return 是否满足条件
     */
    private boolean isIgnorableSchemaError(SQLException ex) {
        return ex.getErrorCode() == 1061 || ex.getErrorCode() == 1060 || ex.getErrorCode() == 1091;
    }

    /**
     * 处理ensureCompatibleURLColumns。
     * @param connection connection值
     */
    private void ensureCompatibleUrlColumns(Connection connection) throws SQLException {
        ensureTextColumn(connection, "biz_task_results", "preview_path");
        ensureTextColumn(connection, "biz_task_results", "download_path");
        ensureTextColumn(connection, "biz_task_results", "remote_url");
        ensureTextColumn(connection, "biz_material_assets", "local_storage_path");
        ensureTextColumn(connection, "biz_material_assets", "local_file_path");
        ensureTextColumn(connection, "biz_material_assets", "public_url");
        ensureTextColumn(connection, "biz_material_assets", "third_party_url");
        ensureTextColumn(connection, "biz_material_assets", "remote_url");
        ensureColumn(connection, "biz_material_assets", "owner_user_id", "ALTER TABLE `biz_material_assets` ADD COLUMN `owner_user_id` bigint unsigned DEFAULT NULL COMMENT '归属用户ID' AFTER `material_asset_id`");
        ensureColumn(connection, "biz_material_assets", "workflow_id", "ALTER TABLE `biz_material_assets` ADD COLUMN `workflow_id` varchar(64) NOT NULL DEFAULT '' COMMENT '关联工作流ID' AFTER `task_id`");
        ensureColumn(connection, "biz_material_assets", "stage_type", "ALTER TABLE `biz_material_assets` ADD COLUMN `stage_type` varchar(32) NOT NULL DEFAULT '' COMMENT '阶段类型' AFTER `asset_role`");
        ensureColumn(connection, "biz_material_assets", "clip_index", "ALTER TABLE `biz_material_assets` ADD COLUMN `clip_index` int NOT NULL DEFAULT '0' COMMENT '镜头序号' AFTER `stage_type`");
        ensureColumn(connection, "biz_material_assets", "version_no", "ALTER TABLE `biz_material_assets` ADD COLUMN `version_no` int NOT NULL DEFAULT '0' COMMENT '版本号' AFTER `clip_index`");
        ensureColumn(connection, "biz_material_assets", "selected_for_next", "ALTER TABLE `biz_material_assets` ADD COLUMN `selected_for_next` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否被选为继续依据' AFTER `version_no`");
        ensureColumn(connection, "biz_material_assets", "user_rating", "ALTER TABLE `biz_material_assets` ADD COLUMN `user_rating` int DEFAULT NULL COMMENT '用户评分' AFTER `selected_for_next`");
        ensureColumn(connection, "biz_material_assets", "rating_note", "ALTER TABLE `biz_material_assets` ADD COLUMN `rating_note` varchar(1000) NOT NULL DEFAULT '' COMMENT '评分备注' AFTER `user_rating`");
    }

    /**
     * 处理ensure文本Column。
     * @param connection connection值
     * @param tableName tableName值
     * @param columnName columnName值
     */
    private void ensureTextColumn(Connection connection, String tableName, String columnName) throws SQLException {
        ColumnInfo column = loadColumnInfo(connection, tableName, columnName);
        if (column == null || column.isWideText()) {
            return;
        }
        try (Statement statement = connection.createStatement()) {
            statement.execute("ALTER TABLE `" + tableName + "` MODIFY COLUMN `" + columnName + "` TEXT NOT NULL");
        }
    }

    private void ensureColumn(Connection connection, String tableName, String columnName, String alterSql) throws SQLException {
        if (loadColumnInfo(connection, tableName, columnName) != null) {
            return;
        }
        try (Statement statement = connection.createStatement()) {
            statement.execute(alterSql);
        }
    }

    /**
     * 加载Column信息。
     * @param connection connection值
     * @param tableName tableName值
     * @param columnName columnName值
     * @return 处理结果
     */
    private ColumnInfo loadColumnInfo(Connection connection, String tableName, String columnName) throws SQLException {
        DatabaseMetaData metadata = connection.getMetaData();
        try (ResultSet resultSet = metadata.getColumns(connection.getCatalog(), null, tableName, columnName)) {
            if (!resultSet.next()) {
                return null;
            }
            return new ColumnInfo(
                resultSet.getString("TYPE_NAME"),
                resultSet.getInt("COLUMN_SIZE")
            );
        }
    }

    /**
     * 处理Column信息。
     * @param typeName 类型Name值
     * @param size size值
     * @return 处理结果
     */
    private record ColumnInfo(String typeName, int size) {
        /**
         * 检查是否Wide文本。
         * @return 是否满足条件
         */
        boolean isWideText() {
            String normalized = typeName == null ? "" : typeName.trim().toUpperCase();
            if ("TEXT".equals(normalized) || "MEDIUMTEXT".equals(normalized) || "LONGTEXT".equals(normalized)
                || "LONGVARCHAR".equals(normalized) || "CLOB".equals(normalized)) {
                return true;
            }
            return size >= 4096;
        }
    }
}
