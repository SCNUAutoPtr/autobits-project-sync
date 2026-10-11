# AutoBits Project Sync

SCNUAutoPtr 组织级 Issue 看板的同步代码。

**[打开全局看板](https://github.com/orgs/SCNUAutoPtr/projects/7)** · [按负责人](https://github.com/orgs/SCNUAutoPtr/projects/7/views/2) · [未分配](https://github.com/orgs/SCNUAutoPtr/projects/7/views/3) · [任务关系](https://github.com/orgs/SCNUAutoPtr/projects/7/views/4)

公共仓库只保存自动化代码和配置说明。Issue 数据保留在源仓库与私有 Project；不会生成公开的数据文件，公共 Actions 日志不输出私有 Issue 的标题、正文、人员或关系详情。

## 看板视图

| 视图 | 用途 |
| --- | --- |
| 全局总览 | 活跃仓库的全部未关闭 Issue |
| 按负责人 | 按原生 Assignees 分组，查看任务分配 |
| 未分配 | 没有负责人的活跃任务 |
| 任务关系 | 按原生 Parent issue 分组，查看子任务进度、阻塞方与下游 |
| 当前阻塞 | 存在尚未关闭的原生 blocked-by 依赖 |
| 按仓库 | 按原生 Repository 分组 |
| 我的任务 | assignee:@me |
| 归档遗留 | 已归档仓库中仍未关闭的 Issue |
| 已完成 | 关闭原因为 completed 的已收录任务 |
| 任务分配看板 | 按仓库泳道、按分配情况分列 |
| 不再计划 | 关闭原因为 not_planned 的已收录任务 |

GitHub Issues 是唯一事实源。负责人、标签、里程碑、父子关系和子任务进度使用 GitHub 原生字段，随 Issue 更新；仓库范围、分配情况、结案类型、依赖情况、阻塞方、下游及正文关联引用由脚本同步。

“已分配”不代表开始执行。正文中的 Issue 链接仅作为引用，不推断正式依赖。已解除的依赖与尚未关闭的依赖分别标识。专项 Project 保持独立。

## 使用 GitHub App

建议使用专用组织 App。每次工作流生成短期 installation token，结束后撤销；不保存个人 PAT，也不复用 Jenkins 或其他集成的 App。

1. 在 SCNUAutoPtr 创建 GitHub App，安装范围选 **Only on this account**，关闭 **Active webhook**。
2. 设置以下权限，其余均为 No access：
   - Repository → **Issues: Read-only**。
   - Repository → **Metadata: Read-only**（GitHub 自动要求）。
   - Organization → **Projects: Read and write**。
3. 安装到 **SCNUAutoPtr → All repositories**。该范围覆盖私有仓库、新仓库和归档遗留；Project 继续保持私有。
4. 生成 private key，在本仓库 **Settings → Secrets and variables → Actions** 配置：

| 类型 | 名称 | 值 |
| --- | --- | --- |
| Variable | `GH_APP_ID` | App ID，非 Client ID 或 Installation ID |
| Secret | `GH_APP_PRIVATE_KEY` | 完整 PEM private key |

凭据仅保存在 GitHub Actions Secrets，不要提交到 Git 或发送到 Issue、PR、聊天。App 不需要 Contents、Actions 或 Issues 写权限；工作流检出本公共仓库使用独立的、只读 `GITHUB_TOKEN`。

配置完成后，在 **Actions → Sync global issue board → Run workflow** 手动运行一次。工作流每 30 分钟定时同步，GitHub 调度可能延迟。未配置凭据时，工作流明确跳过同步，不会显示为已经同步。

GitHub 会在公共仓库连续 60 天没有仓库活动时自动停用定时工作流；如遇停用，在 Actions 中重新启用。日常检查可通过工作流运行记录核对最近一次真实同步。

公共仓库的标准 GitHub-hosted runner 不占用私有仓库的 Actions 分钟配额。

## 同步边界

- 初始与后续同步收录组织全部未关闭 Issue，历史已收录、之后关闭的 Issue 保留。
- 脚本可重复运行，只写 Project #7 的收录与投影字段；不删除卡片，不修改源 Issue、负责人或标签，不创建或重写父子和阻塞关系，不关闭任务。
- 从组织 Project 写权限这一 GitHub 权限粒度出发，脚本仍明确限定写入 Project #7。
- 关联字段同步需要 App 对全部目标仓库有 Issues 读取权限。选择少量仓库安装会降低覆盖范围。
- 不触发 `pull_request` 或 `pull_request_target`；只有默认分支的定时工作流和显式手动运行能使用 App 凭据。工作流检出固定的 `main`，官方 Actions 固定到 commit SHA。
- 本工作流只授予 installation token **Issues: read** 和 **Organization Projects: write**，而不是继承额外 App 权限。
- 同一组工作流串行运行，避免并发更新。
- 未关闭 Issue 超过 GitHub Search 的 1000 条上限，或单 Issue 原生关系超过查询容量时，脚本明确报错，须扩展分页后继续；不会用截断结果宣称同步完整。
- GitHub Search 可能存在短暂索引延迟，下一次定时同步会再次校正。

本机也可用已授权的 GitHub 登录运行（不要把凭据写入命令或代码）：

```sh
python3 scripts/global-project-sync.py
```

本机输出汇总数量，公共 Actions 只输出同步进度与校验结果。鉴权与 GraphQL 错误不打印原始响应，避免把私有数据写入公共日志。
