package com.jiandou.api.auth.security;

import com.jiandou.api.auth.domain.UserStatus;
import com.jiandou.api.auth.infrastructure.mybatis.SysUserEntity;
import java.io.Serializable;
import java.util.Collection;
import java.util.List;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;

/**
 * 当前登录用户主体。
 */
public record CurrentUserPrincipal(
    Long userId,
    String username,
    String displayName,
    String role,
    String status
) implements Serializable {

    /**
     * 构造主体。
     * @param user 用户实体
     * @return 处理结果
     */
    public static CurrentUserPrincipal from(SysUserEntity user) {
        return new CurrentUserPrincipal(
            user.getId(),
            user.getUsername(),
            user.getDisplayName(),
            user.getRole(),
            user.getStatus()
        );
    }

    /**
     * 返回授权集合。
     * @return 处理结果
     */
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return List.of(new SimpleGrantedAuthority("ROLE_" + role));
    }

    /**
     * 检查是否可用。
     * @return 是否满足条件
     */
    public boolean isEnabled() {
        return UserStatus.ACTIVE.value().equals(status);
    }
}
