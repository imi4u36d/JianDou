package com.jiandou.api.auth.web;

import com.jiandou.api.auth.application.AdminIdentityService;
import com.jiandou.api.auth.security.CurrentUserPrincipal;
import com.jiandou.api.auth.web.dto.AdminInviteResponse;
import com.jiandou.api.auth.web.dto.AdminUserResponse;
import com.jiandou.api.auth.web.dto.CreateInviteRequest;
import com.jiandou.api.config.ApiPathConstants;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端身份管理控制器。
 */
@RestController
@RequestMapping(ApiPathConstants.ADMIN)
public class AdminIdentityController {

    private final AdminIdentityService adminIdentityService;

    public AdminIdentityController(AdminIdentityService adminIdentityService) {
        this.adminIdentityService = adminIdentityService;
    }

    /**
     * 列出用户。
     * @return 处理结果
     */
    @GetMapping("/users")
    public List<AdminUserResponse> listUsers() {
        return adminIdentityService.listUsers();
    }

    /**
     * 禁用用户。
     * @param id 用户ID
     * @param actor 当前管理员
     * @return 处理结果
     */
    @PostMapping("/users/{id}/disable")
    public AdminUserResponse disableUser(@PathVariable Long id, @AuthenticationPrincipal CurrentUserPrincipal actor) {
        return adminIdentityService.disableUser(id, actor);
    }

    /**
     * 启用用户。
     * @param id 用户ID
     * @return 处理结果
     */
    @PostMapping("/users/{id}/enable")
    public AdminUserResponse enableUser(@PathVariable Long id) {
        return adminIdentityService.enableUser(id);
    }

    /**
     * 列出邀请码。
     * @return 处理结果
     */
    @GetMapping("/invites")
    public List<AdminInviteResponse> listInvites() {
        return adminIdentityService.listInvites();
    }

    /**
     * 创建邀请码。
     * @param request 创建请求
     * @param actor 当前管理员
     * @return 处理结果
     */
    @PostMapping("/invites")
    public AdminInviteResponse createInvite(
        @Valid @RequestBody CreateInviteRequest request,
        @AuthenticationPrincipal CurrentUserPrincipal actor
    ) {
        return adminIdentityService.createInvite(request, actor);
    }

    /**
     * 撤销邀请码。
     * @param id 邀请码ID
     * @return 处理结果
     */
    @PostMapping("/invites/{id}/revoke")
    public AdminInviteResponse revokeInvite(@PathVariable Long id) {
        return adminIdentityService.revokeInvite(id);
    }
}
