# 公寓租客续租因素分析

海棠湾租客关系组用房源档案、服务事件和续租问卷解释租客续租意愿，并把客户经理动作落到可执行的跟进清单。

## 真实场景

客户团队是海棠湾租客关系组，管理滨江北岸、老城西区和新港片区的公寓。当前流程由运营同事在表格里维护房源和租客，在工单系统里看报修，在月底把问卷结果复制到另一张表再讨论续租。痛点是服务解决时长与续租意愿无法连起来，重复问卷会污染样本，客户经理拿到的是平均数而不是可执行的租客名单。本应用替代“服务事件整理→问卷复核→因素解释→客户经营分派”这段工作流，下游由客户经理和服务协调员消费。

## 业务主流程

入住服务 → 问卷采集 → 偏相关 / 逐步回归解释 → 客户经营复核 → 跟进清单。

已实现的领域异常包括同一租客同一租期的问卷重复返回 `409`，已退租租客提交问卷返回 `422`，且不生成跟进任务。客户经理复核后只为活跃租客生成跟进任务。

## 功能模块

- 房源档案，查看房源、租金、房龄、租客和在住状态
- 报修服务，登记服务事件并保留解决时长、评分和状态
- 问卷采集，记录四类体验评分、续租意愿和租客原话
- 因素分析，Python 计算控制租金压力与房龄的偏相关，以及逐步回归特征解释
- 续租跟进，客户经理复核后生成并关闭跟进任务
- JWT 三角色、审计日志、请求响应追踪和后端错误反馈

## 启动

```bash
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
```

访问 `http://localhost:18258`。

演示账号密码均为 `rental123`。

| 账号 | 角色 | 主要动作 |
|---|---|---|
| `analyst@harborstay.local` | analyst | 查看数据，运行分析，采集问卷 |
| `manager@harborstay.local` | customer_manager | 客户经营复核，生成/关闭跟进任务 |
| `service@harborstay.local` | service_coordinator | 登记报修服务，查看房源与租客 |

## 枚举位置

- 角色枚举：`backend/src/db.py` 与 `backend/src/auth.py`，前端展示在 `frontend/src/app.js`
- 租客状态：`backend/src/db.py` 的 `active / moved_out`
- 服务状态和紧急度：`backend/src/db.py`、`backend/src/schemas.py`
- 问卷状态和跟进任务优先级：`backend/src/db.py`、`frontend/src/app.js`

## 目录与技术栈

- `frontend`：Nginx 托管的原生 HTML/CSS/ES modules
- `backend`：Python 3.11、FastAPI、Psycopg、PyJWT
- `worker`：共享卷心跳 worker，为后台任务槽位保活
- `db`：PostgreSQL 16
- `redis`：Redis 7

## 开发与数据

本地后端可用 `uvicorn src.main:app --reload` 启动。`backend/scripts/seed_demo.py` 使用自然键 upsert 逻辑，可连续运行而不新增房源、租客、服务事件或问卷。模型输入和输出在 `backend/src/analysis.py`，数据持久化与业务规则在 `backend/src/services.py` 与 `backend/src/main.py`。

## License

Internal evaluation artifact.

## 续租跟进后的业务办理

| 模块 | 客户经理 | 服务协调员 | 数据分析师 |
|---|---|---|---|
| 续租阻碍整改 | 绑定本租客报修和续租跟进，承诺日期，验收或退回 | 提交维修或复测证据 | 查阅整改和原报修实绩 |
| 退租交接排班 | 预约及取消验房交接 | 登记钥匙数、验房记录索引和房况 | 查阅交接结果 |
| 续租意愿偏差复核 | 登记签约或交接结果与依据，可补正退回单 | 查阅 | 退回或确认样本，查看分组实绩 |

跟进任务保存原租期结束日期。整改须关联同一租客和房源的有效报修。经理验收后，未完报修改为已结修，实际用时为首次报修至本次报验的时长；已有结修事件保留原记录。报验日在承诺日之后时标记超期。

交接时间按北京时间录入，可选择 30、60 或 90 分钟。预约日期须在当前租期结束前 30 日至结束后 7 日，同一房源期间互斥。实际交接仍有同住租客时保留房源在住状态。协调员完成交接后更新退租状态，并取消该租期尚未完成的留租整改。

经理用签约凭证或已完成的交接登记实绩，分析师确认后才纳入低、中、高意愿三组。续租记 10 分，退租记 0 分，偏差是实绩分减去问卷意愿；续租率按组内已确认样本计算。确认续租同时延长租期，确认任一结果都结束原跟进。分组统计的分母为本工作台已确认的跟进样本。

扩展接口位于 `/resident-operations/remedies`、`/resident-operations/checkouts` 和 `/resident-operations/outcomes`。新增枚举在 `backend/migrations/002_resident_outcomes.sql`、`backend/src/resident_inputs.py`、`backend/src/resident_operations.py` 与 `frontend/src/resident-operations.js` 同步。启动会为已有跟进补填当时可用的租期结束日期，并保留后续写入的原租期快照。

## 续租报价、合同与首账单

1. 客户经理按房源片区和月份登记可让利额度。已批准和已签署报价共用额度，审批时按租期累计月租优惠并检查余额。
2. 客户经理依据原续租跟进提交报价，数据分析师审批或退回。已有有效报价时，关闭退租预约入口，避免同一租期并行办理互斥手续。
3. 客户经理登记续租合同凭证。系统核对租期、租金和报价，再按首月实际占用天数生成应收。服务协调员录入实际首账单，差异经更正后保留各版金额与凭证。
4. 客户经理根据已签合同、匹配的首账单和报价租期登记续租实绩。数据分析师确认后，系统才延长原租期并更新按意愿分组的统计。
