# JianDou（煎豆）

JianDou 是一个文本到视频工作台。上传小说章节、粘贴正文或输入提示词，即可通过可配置的多模型链路生成视频。

## 快速启动

```bash
# 1. 配置模型 API Key
#    编辑 config/model/providers.secrets.yml，填入各厂商密钥
```

**方式一：Docker**

```bash
docker build -t jiandou .
docker run -d -p 80:8000 -v ./config:/app/config -v ./storage:/app/storage jiandou
```

**方式二：本地命令**

```bash
# 首次需安装依赖
npm install
jiandou serve
```

启动后访问：
- 用户前台：`http://127.0.0.1`
- 管理后台：`http://127.0.0.1/admin`

## 工作流程

```
文本输入 ──▶ 文本模型(生成分镜/提示词)
                ──▶ 视觉模型(理解参考图)
                        ──▶ 关键帧模型(生成首尾帧)
                                ──▶ 视频模型(生成视频)
                                        ──▶ 预览/下载/评分
```

每一段模型均可独立选择厂商和模型版本，按需组合。

## 能力概述

**创作输入**
- 上传 TXT 文件或直接粘贴正文，自动提取内容生成提示词
- 也可直接输入自定义提示词，灵活控制生成方向
- 支持参考图作为关键帧的首帧或尾帧

**生成控制**
- 多段模型链路（文本/视觉/关键帧/视频）支持不同厂商自由组合
- 输出参数动态约束：画幅、清晰度、时长区间、生成数量、Seed 等
- 参数选项会根据所选视频模型的能力自动过滤，避免无效配置

**任务管理**
- 实时查看任务进度、阶段状态、耗时和视频预览
- 支持任务的创建、筛选、详情查看
- 支持重试、暂停、继续、终止、删除、评分等运维操作

**Seed 管理**
- 自动汇总高评分任务中的可用 Seed
- 支持一键回填 Seed 到当前任务，提升稳定出片效率

**管理后台**
- 独立的管理后台，与用户前台分离
- 适合内容生产团队和管理运维分层协作

## 模型配置

模型配置集中在 `config/model/` 目录：

```
config/model/
├── models.yml                  # 可选模型列表定义
├── providers/                  # 各厂商基础配置（base_url 等）
│   ├── aliyun.yml
│   ├── volcengine.yml
│   └── openai.yml
└── providers.secrets.yml       # API Key 覆盖（不提交到仓库）
```

支持的厂商：阿里云（通义千问/万相）、火山引擎（豆包/Seedream/Seedance）、OpenAI 兼容接口。

## 社区与支持

- QQ 交流群：`1090387362`
- [报告 Bug / 功能建议](https://github.com/imi4u36d/JianDou/issues)

## Star History

<a href="https://www.star-history.com/?repos=imi4u36d%2FJianDou&type=date&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=imi4u36d/JianDou&type=date&legend=top-left" />
  </picture>
</a>

## License

本项目采用仓库内的 [License](./License)。
