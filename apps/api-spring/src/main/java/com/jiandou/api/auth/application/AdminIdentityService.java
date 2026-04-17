package com.jiandou.api.auth.application;

import com.jiandou.api.auth.domain.UserRole;
import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.MybatisAuthRepository;
import com.jiandou.api.auth.infrastructure.mybatis.SysInviteCodeEntity;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import com.jiandou.api.auth.security.CurrentUserPrincipal;
import com.jiandou.api.auth.web.dto.AdminInviteActorResponse;
import com.jiandou.api.auth.web.dto.AdminInviteResponse;
import com.jiandou.api.auth.web.dto.AdminUserResponse;
import com.jiandou.api.auth.web.dto.CreateInviteRequest;
import com.jiandou.api.common.exception.ApiException;
import com.jiandou.api.config.JiandouAuthProperties;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;

/**
 * 管理端用户与邀请码服务。
 */
@Service
public class AdminIdentityService {

    private final MybatisAuthRepository authRepository;
    private final JiandouAuthProperties authProperties;

    public AdminIdentityService(MybatisAuthRepository authRepository, JiandouAuthProperties authProperties) {
        this.authRepository = authRepository;
        this.authProperties = authProperties;
    }

    /**
     * 列出用户。
     * @return 处理结果
     */
    public List<AdminUserResponse> listUsers() {
        return authRepository.listUsers().stream().map(this::toUserResponse).toList();
    }

    /**
     * 禁用用户。
     * @param id 用户ID
     * @param actor 当前操作者
     * @return 处理结果
     */
    public AdminUserResponse disableUser(Long id, CurrentUserPrincipal actor) {
        SysUserEntity user = requireUser(id);
        if (UserStatus.DISABLED.value().equals(user.getStatus())) {
            return toUserResponse(user);
        }
        if (UserRole.ADMIN.value().equals(user.getRole()) && authRepository.countActiveAdmins() <= 1) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "last_admin_guard", "至少保留一个可登录的管理员账号");
        }
        return toUserResponse(authRepository.updateUserStatus(id, UserStatus.DISABLED));
    }

    /**
     * 启用用户。
     * @param id 用户ID
     * @return 处理结果
     */
    public AdminUserResponse enableUser(Long id) {
        requireUser(id);
        return toUserResponse(authRepository.updateUserStatus(id, UserStatus.ACTIVE));
    }

    /**
     * 列出邀请码。
     * @return 处理结果
     */
    public List<AdminInviteResponse> listInvites() {
        List<SysInviteCodeEntity> invites = authRepository.listInvites();
        Set<Long> relatedUserIds = new LinkedHashSet<>();
        for (SysInviteCodeEntity invite : invites) {
            if (invite.getCreatedBy() != null) {
                relatedUserIds.add(invite.getCreatedBy());
            }
            if (invite.getUsedBy() != null) {
                relatedUserIds.add(invite.getUsedBy());
            }
        }
        Map<Long, SysUserEntity> userMap = authRepository.findUsersByIds(relatedUserIds);
        return invites.stream().map(invite -> toInviteResponse(invite, userMap)).toList();
    }

    /**
     * 创建邀请码。
     * @param request 创建请求
     * @param actor 当前操作者
     * @return 处理结果
     */
    public AdminInviteResponse createInvite(CreateInviteRequest request, CurrentUserPrincipal actor) {
        UserRole role = UserRole.from(request.role());
        OffsetDateTime expiresAt = request.expiresAt();
        if (expiresAt == null) {
            expiresAt = OffsetDateTime.now().plusDays(authProperties.getInviteDefaultExpiryDays());
        }
        if (!expiresAt.isAfter(OffsetDateTime.now())) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "invalid_invite_expiry", "邀请码过期时间必须晚于当前时间");
        }
        SysInviteCodeEntity invite = authRepository.createInvite(role, expiresAt, actor.userId());
        Map<Long, SysUserEntity> userMap = authRepository.findUsersByIds(Set.of(actor.userId()));
        return toInviteResponse(invite, userMap);
    }

    /**
     * 撤销邀请码。
     * @param id 邀请码ID
     * @return 处理结果
     */
    public AdminInviteResponse revokeInvite(Long id) {
        SysInviteCodeEntity invite = authRepository.revokeInvite(id);
        Set<Long> relatedUserIds = new LinkedHashSet<>();
        if (invite.getCreatedBy() != null) {
            relatedUserIds.add(invite.getCreatedBy());
        }
        if (invite.getUsedBy() != null) {
            relatedUserIds.add(invite.getUsedBy());
        }
        return toInviteResponse(invite, authRepository.findUsersByIds(relatedUserIds));
    }

    private SysUserEntity requireUser(Long id) {
        SysUserEntity user = authRepository.findUserById(id);
        if (user == null) {
            throw new ApiException(HttpStatus.NOT_FOUND, "user_not_found", "用户不存在");
        }
        return user;
    }

    private AdminUserResponse toUserResponse(SysUserEntity user) {
        return new AdminUserResponse(
            user.getId(),
            user.getUsername(),
            user.getDisplayName(),
            user.getRole(),
            user.getStatus(),
            user.getLastLoginAt(),
            user.getCreatedAt(),
            user.getUpdatedAt()
        );
    }

    private AdminInviteResponse toInviteResponse(SysInviteCodeEntity invite, Map<Long, SysUserEntity> userMap) {
        return new AdminInviteResponse(
            invite.getId(),
            invite.getCode(),
            invite.getRole(),
            invite.getStatus(),
            invite.getExpiresAt(),
            toInviteActor(userMap.get(invite.getCreatedBy())),
            toInviteActor(userMap.get(invite.getUsedBy())),
            invite.getUsedAt(),
            invite.getCreatedAt(),
            invite.getUpdatedAt()
        );
    }

    private AdminInviteActorResponse toInviteActor(SysUserEntity user) {
        if (user == null) {
            return null;
        }
        return new AdminInviteActorResponse(user.getId(), user.getUsername(), user.getDisplayName());
    }
}
