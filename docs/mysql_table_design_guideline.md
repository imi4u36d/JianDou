在 MySQL 数据库设计中，遵循**数据库设计三范式（3NF）**以及行业通用的规范（如阿里规约）是保证系统稳定性和扩展性的关键。

以下我为你整理的一份标准的 **MySQL 建表规范指南**，以及一个符合规范的**示例脚本**。

---

## 1. 核心设计规范

### 命名规范
* **库名、表名、字段名**：必须使用小写字母，单词间用下划线（`_`）分割。例如：`user_order`。
* **见名知意**：禁止使用缩写或无意义的名称（如 `t1`, `col_a`）。
* **表前缀**：建议带上业务模块前缀，如 `trade_order`。

### 字段规范
* **主键设计**：每张表必须有主键，建议使用 `unsigned bigint` 自增 ID，且命名为 `id`。
* **禁止使用 NULL**：所有字段尽量设置为 `NOT NULL`，并给出默认值。`NULL` 会增加索引维护成本且容易产生逻辑陷阱。
* **时间字段**：统一使用 `datetime` 或 `timestamp`，避免使用字符串存储时间。
* **数值类型**：
    * 状态、类型、性别：使用 `tinyint`。
    * 金额：禁止使用 `float/double`，必须使用 `decimal` 以防精度丢失。

### 必备字段（审计字段）
每一张规范的表都应该包含以下五个字段：
1.  `id`：主键。
2.  `create_time`：创建时间。
3.  `update_time`：修改时间。
4.  `is_deleted`：逻辑删除标记（1：已删，0：正常）。
5.  `remark`：备注（视情况而定）。

---

## 2. 规范建表 SQL 示例

假设我们要设计一个**用户信息表**：

```sql
CREATE TABLE `sys_user` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `username` varchar(32) NOT NULL COMMENT '用户账号',
  `nickname` varchar(32) NOT NULL DEFAULT '' COMMENT '用户昵称',
  `password` varchar(128) NOT NULL COMMENT '加密后的密码',
  `email` varchar(64) DEFAULT '' COMMENT '邮箱地址',
  `mobile` char(11) NOT NULL DEFAULT '' COMMENT '手机号码',
  `user_status` tinyint NOT NULL DEFAULT '1' COMMENT '状态: 0-禁用, 1-正常',
  `is_deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除: 0-未删, 1-已删',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `version` int NOT NULL DEFAULT '0' COMMENT '乐观锁版本号',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_mobile` (`mobile`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统用户表';
```

---

## 3. 关键点深度解析

### 存储引擎与字符集
* **Engine**: 必须使用 `InnoDB`（支持事务、行级锁）。
* **Charset**: 统一使用 `utf8mb4`。不要用 `utf8`，因为 `utf8` 无法存储表情（Emoji）和部分生僻字。

### 索引规范
* **索引命名**：
    * 唯一索引：`uk_字段名` (Unique Key)
    * 普通索引：`idx_字段名` (Index)
* **数量限制**：单表索引建议不超过 5 个，过多的索引会严重影响 `INSERT` 和 `UPDATE` 的效率。

### 关于外键
* **物理外键 vs 逻辑外键**：在互联网高并发场景下，**禁止**使用数据库物理外键（`FOREIGN KEY`）。约束关系应通过程序逻辑（Service 层）来保证，以提高集群性能和降低耦合。

---

## 4. 数据库设计三范式（简述）
为了让表结构更科学，通常需要满足：
1.  **第一范式 (1NF)**：字段不可再分（原子性）。
2.  **第二范式 (2NF)**：非主键字段必须完全依赖于主键，不能只依赖一部分。
3.  **第三范式 (3NF)**：非主键字段不能相互依赖（消除传递依赖）。

---

您是正在为新项目搭建基础架构，还是在重构旧有的数据库系统？
