<template>
  <section class="credit-page">
    <el-card class="surface-card" shadow="never">
      <template #header>
        <div class="credit-page__toolbar">
          <span class="credit-page__toolbar-spacer" aria-hidden="true"></span>
          <el-button :icon="Refresh" plain @click="refreshActiveTab">刷新</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="credit-page__tabs" @tab-change="handleTabChange">
        <el-tab-pane label="用户积分" name="users">
          <el-form class="credit-page__filters" inline @submit.prevent="loadCreditUsers">
            <el-form-item label="关键词">
              <el-input v-model.trim="userFilters.q" clearable placeholder="用户名 / 显示名" />
            </el-form-item>
            <el-form-item class="credit-page__filters-action">
              <el-button :loading="loadingUsers" native-type="submit" type="primary">查询</el-button>
            </el-form-item>
          </el-form>

          <el-alert
            v-if="userErrorMessage"
            :closable="false"
            class="credit-page__alert"
            show-icon
            type="error"
            :title="userErrorMessage"
          />

          <el-table v-loading="loadingUsers" :data="creditUsers" class="credit-page__table">
            <el-table-column label="用户" min-width="180">
              <template #default="{ row }">
                <div class="credit-page__primary-cell">
                  <strong>{{ row.username }}</strong>
                </div>
              </template>
            </el-table-column>
            <el-table-column align="right" label="当前积分" min-width="120" prop="balance" />
            <el-table-column align="right" label="累计消耗" min-width="120" prop="totalConsumed" />
            <el-table-column align="right" label="累计调整" min-width="120" prop="totalAdjusted" />
            <el-table-column align="right" label="图片次数" min-width="110" prop="imageGenerationCount" />
            <el-table-column align="right" label="视频次数" min-width="110" prop="videoGenerationCount" />
            <el-table-column label="最近使用" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.lastUsedAt) }}
              </template>
            </el-table-column>
            <el-table-column align="right" fixed="right" label="操作" min-width="170">
              <template #default="{ row }">
                <div class="credit-page__actions">
                  <el-button link type="primary" title="流水" aria-label="查看流水" @click="openTransactionDialog(row)">流水</el-button>
                  <el-button link type="warning" title="调整" aria-label="调整积分" @click="openAdjustDialog(row)">调整</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="消耗规则" name="rules">
          <el-alert
            v-if="ruleErrorMessage"
            :closable="false"
            class="credit-page__alert"
            show-icon
            type="error"
            :title="ruleErrorMessage"
          />

          <el-table v-loading="loadingRules" :data="creditRules" class="credit-page__table">
            <el-table-column label="功能" min-width="180">
              <template #default="{ row }">
                <div class="credit-page__primary-cell">
                  <strong>{{ row.displayName || row.featureCode }}</strong>
                  <span>{{ row.featureCode }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column align="right" label="单次消耗" min-width="120" prop="cost" />
            <el-table-column label="更新时间" min-width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updatedAt) }}
              </template>
            </el-table-column>
            <el-table-column align="right" fixed="right" label="操作" min-width="120">
              <template #default="{ row }">
                <el-button link type="primary" title="编辑规则" aria-label="编辑规则" @click="openRuleDialog(row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="transactionDialogVisible" :title="transactionDialogTitle" width="900px">
      <el-table v-loading="loadingTransactions" :data="transactions" class="credit-page__table">
        <el-table-column label="时间" min-width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="类型" min-width="120">
          <template #default="{ row }">
            <el-tag :type="transactionTagType(row.amountDelta)" effect="light">
              {{ transactionTypeLabel(row.transactionType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column align="right" label="变动" min-width="100">
          <template #default="{ row }">
            <span :class="row.amountDelta >= 0 ? 'credit-page__positive' : 'credit-page__negative'">
              {{ formatSignedNumber(row.amountDelta) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column align="right" label="变动前" min-width="100" prop="balanceBefore" />
        <el-table-column align="right" label="变动后" min-width="100" prop="balanceAfter" />
        <el-table-column label="功能" min-width="130" prop="featureCode" />
        <el-table-column label="原因" min-width="220" prop="reason" show-overflow-tooltip />
      </el-table>
    </el-dialog>

    <el-dialog v-model="adjustDialogVisible" :title="adjustDialogTitle" width="460px">
      <el-form label-position="top">
        <el-form-item label="调整数量">
          <el-input-number v-model="adjustForm.amount" :step="10" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="调整原因">
          <el-input
            v-model.trim="adjustForm.reason"
            maxlength="200"
            placeholder="调整原因"
            show-word-limit
            type="textarea"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button :loading="submittingAdjustment" type="primary" @click="submitAdjustment">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ruleDialogVisible" :title="ruleDialogTitle" width="420px">
      <el-form label-position="top">
        <el-form-item label="单次消耗积分">
          <el-input-number v-model="ruleForm.cost" :min="0" :step="5" controls-position="right" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button :loading="submittingRule" type="primary" @click="submitRule">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { Refresh } from "@element-plus/icons-vue";
import {
  adminTransactionTypeLabel as transactionTypeLabel,
  formatCreditDateTime as formatDateTime,
  formatSignedCreditAmount as formatSignedNumber,
  transactionTagType,
} from "@/admin/features/credits/credit-management-presenters";
import { useCreditManagement } from "@/admin/composables/useCreditManagement";

const {
  activeTab, loadingUsers, loadingRules, loadingTransactions, submittingAdjustment, submittingRule,
  userErrorMessage, ruleErrorMessage, creditUsers, creditRules, transactions, transactionDialogVisible,
  adjustDialogVisible, ruleDialogVisible, userFilters, adjustForm, ruleForm, transactionDialogTitle,
  adjustDialogTitle, ruleDialogTitle, loadCreditUsers, refreshActiveTab, handleTabChange,
  openTransactionDialog, openAdjustDialog, submitAdjustment, openRuleDialog, submitRule,
} = useCreditManagement();
</script>

<style scoped src="./credit-management-view.css"></style>
