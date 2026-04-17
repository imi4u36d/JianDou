package com.jiandou.api.auth.infrastructure.mybatis;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.jiandou.api.auth.domain.InviteStatus;
import com.jiandou.api.auth.domain.UserRole;
import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.common.exception.ApiException;
import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.apache.ibatis.session.SqlSession;
import org.apache.ibatis.session.SqlSessionFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Repository;

/**
 * 鉴权相关持久化仓储。
 */
@Repository
public class MybatisAuthRepository {

    private static final String INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

    private final SqlSessionFactory sqlSessionFactory;
    private final SecureRandom secureRandom = new SecureRandom();

    public MybatisAuthRepository(SqlSessionFactory sqlSessionFactory) {
        this.sqlSessionFactory = sqlSessionFactory;
    }

    /**
     * 按用户名查询用户。
     * @param username 用户名
     * @return 处理结果
     */
    public SysUserEntity findUserByUsername(String username) {
        if (username == null || username.isBlank()) {
            return null;
        }
        try (SqlSession session = sqlSessionFactory.openSession()) {
            SysUserMapper mapper = session.getMapper(SysUserMapper.class);
            return mapper.selectOne(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .eq(SysUserEntity::getUsername, normalizeUsername(username))
                    .last("LIMIT 1")
            );
        }
    }

    /**
     * 按主键查询用户。
     * @param id 主键ID
     * @return 处理结果
     */
    public SysUserEntity findUserById(Long id) {
        if (id == null) {
            return null;
        }
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(SysUserMapper.class).selectById(id);
        }
    }

    /**
     * 批量查询用户。
     * @param ids 主键列表
     * @return 处理结果
     */
    public Map<Long, SysUserEntity> findUsersByIds(Collection<Long> ids) {
        if (ids == null || ids.isEmpty()) {
            return Map.of();
        }
        try (SqlSession session = sqlSessionFactory.openSession()) {
            List<SysUserEntity> users = session.getMapper(SysUserMapper.class).selectBatchIds(ids);
            Map<Long, SysUserEntity> result = new LinkedHashMap<>();
            for (SysUserEntity user : users) {
                result.put(user.getId(), user);
            }
            return result;
        }
    }

    /**
     * 列出全部用户。
     * @return 处理结果
     */
    public List<SysUserEntity> listUsers() {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            return session.getMapper(SysUserMapper.class).selectList(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .orderByAsc(SysUserEntity::getRole)
                    .orderByAsc(SysUserEntity::getStatus)
                    .orderByDesc(SysUserEntity::getCreatedAt)
            );
        }
    }

    /**
     * 统计管理员数量。
     * @return 处理结果
     */
    public long countAdmins() {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            Long count = session.getMapper(SysUserMapper.class).selectCount(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .eq(SysUserEntity::getRole, UserRole.ADMIN.value())
            );
            return count == null ? 0L : count;
        }
    }

    /**
     * 统计活跃管理员数量。
     * @return 处理结果
     */
    public long countActiveAdmins() {
        try (SqlSession session = sqlSessionFactory.openSession()) {
            Long count = session.getMapper(SysUserMapper.class).selectCount(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .eq(SysUserEntity::getRole, UserRole.ADMIN.value())
                    .eq(SysUserEntity::getStatus, UserStatus.ACTIVE.value())
            );
            return count == null ? 0L : count;
        }
    }

    /**
     * 更新最近登录时间。
     * @param userId 用户ID
     * @param lastLoginAt 最近登录时间
     */
    public void updateLastLoginAt(Long userId, OffsetDateTime lastLoginAt) {
        if (userId == null) {
            return;
        }
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            SysUserEntity update = new SysUserEntity();
            update.setLastLoginAt(lastLoginAt);
            session.getMapper(SysUserMapper.class).update(
                update,
                Wrappers.<SysUserEntity>lambdaUpdate().eq(SysUserEntity::getId, userId)
            );
        }
    }

    /**
     * 更新用户状态。
     * @param id 用户ID
     * @param status 新状态
     * @return 处理结果
     */
    public SysUserEntity updateUserStatus(Long id, UserStatus status) {
        try (SqlSession session = sqlSessionFactory.openSession(true)) {
            SysUserEntity update = new SysUserEntity();
            update.setStatus(status.value());
            session.getMapper(SysUserMapper.class).update(
                update,
                Wrappers.<SysUserEntity>lambdaUpdate().eq(SysUserEntity::getId, id)
            );
        }
        return findUserById(id);
    }

    /**
     * 列出全部邀请码。
     * @return 处理结果
     */
    public List<SysInviteCodeEntity> listInvites() {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            SysInviteCodeMapper mapper = session.getMapper(SysInviteCodeMapper.class);
            expireUnusedInvites(session, mapper, OffsetDateTime.now());
            List<SysInviteCodeEntity> invites = mapper.selectList(
                Wrappers.<SysInviteCodeEntity>lambdaQuery()
                    .orderByDesc(SysInviteCodeEntity::getCreatedAt)
            );
            session.commit();
            return invites;
        }
    }

    /**
     * 创建邀请码。
     * @param role 角色
     * @param expiresAt 过期时间
     * @param createdBy 创建人
     * @return 处理结果
     */
    public SysInviteCodeEntity createInvite(UserRole role, OffsetDateTime expiresAt, Long createdBy) {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            SysInviteCodeMapper mapper = session.getMapper(SysInviteCodeMapper.class);
            SysInviteCodeEntity entity = null;
            for (int attempt = 0; attempt < 10 && entity == null; attempt++) {
                String code = generateInviteCode();
                if (mapper.selectOne(
                    Wrappers.<SysInviteCodeEntity>lambdaQuery()
                        .eq(SysInviteCodeEntity::getCode, code)
                        .last("LIMIT 1")
                ) == null) {
                    entity = new SysInviteCodeEntity();
                    entity.setCode(code);
                    entity.setRole(role.value());
                    entity.setStatus(InviteStatus.UNUSED.value());
                    entity.setExpiresAt(expiresAt);
                    entity.setCreatedBy(createdBy);
                    mapper.insert(entity);
                }
            }
            if (entity == null) {
                session.rollback();
                throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "invite_generation_failed", "生成邀请码失败，请稍后重试");
            }
            session.commit();
            return mapper.selectById(entity.getId());
        }
    }

    /**
     * 撤销邀请码。
     * @param id 邀请码ID
     * @return 处理结果
     */
    public SysInviteCodeEntity revokeInvite(Long id) {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            SysInviteCodeMapper mapper = session.getMapper(SysInviteCodeMapper.class);
            SysInviteCodeEntity invite = mapper.selectById(id);
            if (invite == null) {
                throw new ApiException(HttpStatus.NOT_FOUND, "invite_not_found", "邀请码不存在");
            }
            invite = normalizeInviteStatus(session, mapper, invite, OffsetDateTime.now());
            if (InviteStatus.USED.value().equals(invite.getStatus())) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "invite_already_used", "邀请码已被使用，无法撤销");
            }
            if (!InviteStatus.REVOKED.value().equals(invite.getStatus())) {
                SysInviteCodeEntity update = new SysInviteCodeEntity();
                update.setStatus(InviteStatus.REVOKED.value());
                mapper.update(update, Wrappers.<SysInviteCodeEntity>lambdaUpdate().eq(SysInviteCodeEntity::getId, id));
            }
            session.commit();
            return mapper.selectById(id);
        }
    }

    /**
     * 通过邀请码激活账号。
     * @param code 邀请码
     * @param username 用户名
     * @param displayName 显示名
     * @param passwordHash 密码哈希
     * @return 处理结果
     */
    public SysUserEntity activateInvite(String code, String username, String displayName, String passwordHash) {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            SysInviteCodeMapper inviteMapper = session.getMapper(SysInviteCodeMapper.class);
            SysUserMapper userMapper = session.getMapper(SysUserMapper.class);
            OffsetDateTime now = OffsetDateTime.now();
            SysInviteCodeEntity invite = inviteMapper.selectOne(
                Wrappers.<SysInviteCodeEntity>lambdaQuery()
                    .eq(SysInviteCodeEntity::getCode, normalizeInviteCode(code))
                    .last("LIMIT 1 FOR UPDATE")
            );
            if (invite == null) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "invite_not_found", "邀请码不存在");
            }
            invite = normalizeInviteStatus(session, inviteMapper, invite, now);
            if (!InviteStatus.UNUSED.value().equals(invite.getStatus())) {
                throw activateInviteStatusException(invite.getStatus());
            }
            SysUserEntity existingUser = userMapper.selectOne(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .eq(SysUserEntity::getUsername, normalizeUsername(username))
                    .last("LIMIT 1")
            );
            if (existingUser != null) {
                throw new ApiException(HttpStatus.CONFLICT, "username_taken", "用户名已存在");
            }
            SysUserEntity user = new SysUserEntity();
            user.setUsername(normalizeUsername(username));
            user.setDisplayName(displayName);
            user.setPasswordHash(passwordHash);
            user.setRole(invite.getRole());
            user.setStatus(UserStatus.ACTIVE.value());
            userMapper.insert(user);

            SysInviteCodeEntity inviteUpdate = new SysInviteCodeEntity();
            inviteUpdate.setStatus(InviteStatus.USED.value());
            inviteUpdate.setUsedBy(user.getId());
            inviteUpdate.setUsedAt(now);
            inviteMapper.update(inviteUpdate, Wrappers.<SysInviteCodeEntity>lambdaUpdate().eq(SysInviteCodeEntity::getId, invite.getId()));
            session.commit();
            return userMapper.selectById(user.getId());
        }
    }

    /**
     * 引导首个管理员。
     * @param username 用户名
     * @param displayName 显示名
     * @param passwordHash 密码哈希
     * @return 处理结果
     */
    public SysUserEntity bootstrapInitialAdmin(String username, String displayName, String passwordHash) {
        try (SqlSession session = sqlSessionFactory.openSession(false)) {
            SysUserMapper mapper = session.getMapper(SysUserMapper.class);
            Long count = mapper.selectCount(
                Wrappers.<SysUserEntity>lambdaQuery()
                    .eq(SysUserEntity::getRole, UserRole.ADMIN.value())
            );
            if (count != null && count > 0) {
                session.rollback();
                return null;
            }
            SysUserEntity user = new SysUserEntity();
            user.setUsername(normalizeUsername(username));
            user.setDisplayName(displayName);
            user.setPasswordHash(passwordHash);
            user.setRole(UserRole.ADMIN.value());
            user.setStatus(UserStatus.ACTIVE.value());
            mapper.insert(user);
            session.commit();
            return mapper.selectById(user.getId());
        }
    }

    /**
     * 归一化用户名。
     * @param username 用户名
     * @return 处理结果
     */
    public static String normalizeUsername(String username) {
        return username == null ? "" : username.trim().toLowerCase(Locale.ROOT);
    }

    /**
     * 归一化邀请码。
     * @param code 邀请码
     * @return 处理结果
     */
    public static String normalizeInviteCode(String code) {
        return code == null ? "" : code.trim().toUpperCase(Locale.ROOT);
    }

    private void expireUnusedInvites(SqlSession session, SysInviteCodeMapper mapper, OffsetDateTime now) {
        SysInviteCodeEntity update = new SysInviteCodeEntity();
        update.setStatus(InviteStatus.EXPIRED.value());
        mapper.update(
            update,
            Wrappers.<SysInviteCodeEntity>lambdaUpdate()
                .eq(SysInviteCodeEntity::getStatus, InviteStatus.UNUSED.value())
                .isNotNull(SysInviteCodeEntity::getExpiresAt)
                .le(SysInviteCodeEntity::getExpiresAt, now)
        );
        session.flushStatements();
    }

    private SysInviteCodeEntity normalizeInviteStatus(
        SqlSession session,
        SysInviteCodeMapper mapper,
        SysInviteCodeEntity invite,
        OffsetDateTime now
    ) {
        if (invite == null) {
            return null;
        }
        if (InviteStatus.UNUSED.value().equals(invite.getStatus())
            && invite.getExpiresAt() != null
            && !invite.getExpiresAt().isAfter(now)) {
            SysInviteCodeEntity update = new SysInviteCodeEntity();
            update.setStatus(InviteStatus.EXPIRED.value());
            mapper.update(update, Wrappers.<SysInviteCodeEntity>lambdaUpdate().eq(SysInviteCodeEntity::getId, invite.getId()));
            session.flushStatements();
            invite.setStatus(InviteStatus.EXPIRED.value());
        }
        return invite;
    }

    private ApiException activateInviteStatusException(String status) {
        if (InviteStatus.USED.value().equals(status)) {
            return new ApiException(HttpStatus.BAD_REQUEST, "invite_already_used", "邀请码已使用");
        }
        if (InviteStatus.REVOKED.value().equals(status)) {
            return new ApiException(HttpStatus.BAD_REQUEST, "invite_revoked", "邀请码已撤销");
        }
        if (InviteStatus.EXPIRED.value().equals(status)) {
            return new ApiException(HttpStatus.BAD_REQUEST, "invite_expired", "邀请码已过期");
        }
        return new ApiException(HttpStatus.BAD_REQUEST, "invite_invalid", "邀请码不可用");
    }

    private String generateInviteCode() {
        StringBuilder builder = new StringBuilder(12);
        for (int index = 0; index < 12; index++) {
            builder.append(INVITE_CODE_ALPHABET.charAt(secureRandom.nextInt(INVITE_CODE_ALPHABET.length())));
        }
        return builder.toString();
    }
}
