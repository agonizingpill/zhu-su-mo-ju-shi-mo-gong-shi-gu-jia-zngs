# 锐模 · 注塑模具试模工时估价

把模具复杂度转换为可审签的机时成本，贯通工艺规格、估价、机时承诺、现场实绩、净耗结算和客户验收。

模拟客户是锐模工场，32 人模具试制班、M280/M450/M580 三类注塑机。过去工艺员在 Excel 汇总试模，估价凭经验；模腔与滑块交互复杂度不被记录，低价承诺仍占紧缺机时。本项目接收工艺规格与已完成试模记录，替代人工估算、机时核对与报价审签，下游是生产班长的开机承诺。

## 业务模块

- 模具工艺档案：编号唯一，模腔、滑块、钢材、重量有范围约束；修改规格清除旧模型证据。已有计算、申请或生产承诺时禁止修改。
- 试模估价：创建独立估单，配置费率、装夹准备工时、报价；Python worker 真算总机时。
- 误差与工时解释：交叉特征、Ridge 标准化系数，128 条训练与 32 条留出验证，固定 seed 42；展示留出 MAE 和实际/预测散点。
- 机时排程：估价员申请，负责人承诺。底价为预测总工时 × 费率 × 1.15。申请不预占；承诺时行锁核对容量、累加预留并锁单，防止重复承诺或超售。低价或余量不足均不改变已有预留。

- 试模实绩采集：仅已承诺估单开工，一单一份；开工保存预测机时、报价、费率和模具快照。完工时间推导实际机时，良品不得超过总射次；超时完工由负责人填写原因确认。
- 工时偏差结算：已完工实绩计算实际成本、工时偏差与毛利；偏差绝对值超过20%或毛利为负时，签结前必须补足说明。负责人签结同步冻结实绩及结算草稿，拒绝重复签结。

- 模具保养停机：计划→主管批准→保养完检；批准窗口同模具不得重叠。新开工核对停机时间、同模已有running实绩，批准停机也检查未完工试模，避免冲突。已完检保留停机历史，过去已签结数据不改。
- 试模材料领耗：主管树脂批次入库，树脂状态available/quarantine；运行实绩按批次一次领料，锁库存，冻结单价；完工且未建结算可一次退余料，最多退领量。净耗成本=Σ((领kg−退kg)×单价快照)。所有新结算按台账取成本，拒绝任意覆盖；结算建立后领退料冻结。已signed历史数值保持，不补写旧凭据。
- 客户交付验收：只从signed结算交样，样件数≤实绩good_shots；发样→客户签收→接受或整改→主管关闭。整改必须绑定原完工之后新一次同模具signed实绩，旧实绩或其他模具不能替代；重复签收/关闭拒绝。这里只留本地交接和客户意见，不发送外部消息。

## 快速启动

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build
docker compose exec -T backend python -m scripts.seed_demo
```

访问 [工作台](http://localhost:18222)，后端 [API 文档](http://localhost:19222/docs)，数据库端口 17722。五个服务 frontend/backend/worker/db/redis 均配置健康检查；worker 使用 20 秒心跳。Nginx `/api/` 去掉前缀代理后端路由。

|账号|口令|角色|任务与权限|
|---|---|---|---|
|admin@ruimo.demo|Mould2026!|admin|全部读写、开放机时、最终承诺、超时完工与结算签结、保养批准、树脂入库/隔离、客户交付关闭|
|estimator@ruimo.demo|Mould2026!|estimator|录入模具、建立修订估价、估算、申请机时；常规开工完工、保养计划/完检、领退料、客户签收/验收记录、结算草稿；不能承诺或签结|
|viewer@ruimo.demo|Mould2026!|viewer|只读九业务页面与审计|

JWT 8 小时过期，密码 PBKDF2-SHA256 盐化存储。演示账号只用于本地，部署前修改 JWT_SECRET 和数据库演示口令。

## 一天的工作剧本

1. 08:30 查看 `MD-86` 八腔医疗接头模：8 腔、4 滑块、S136、860kg。
2. 09:00 核对 `TR-001`～`TR-160` 完成试模记录。seed 是固定随机数业务模拟数据。
3. 09:30 打开 `QE-26017`，费率 280 元/h、准备工时 2h，客户报价 8000 元。
4. 10:00 后台计算约 15.14h；底价约 4875.08 元；留出 MAE 约 0.262h。
5. 10:30 向 M280 `2026-11-18 08:00` 48h 时段申请机时。
6. 11:00 异常演练：100 元低价承诺被拒；M280 次日 4h 时段不能容纳本单。
7. 14:00 修订报价后重新申请，负责人承诺后预留 15.14h、余量 32.86h。估单与模具规格锁定。
8. 16:00 只读账号查看排程与模型证据；审计接口保留登记、估算、申请、修价、承诺记录。

9. 次日08:00，在「试模实绩采集」选择已承诺 `QE-FLOOR-DEMO` 开工，快照为10h、300元/h、报价5000元。此单是演示用已承诺预算，seed首次建立时为M450预留10h；不冒充模型推理结果。
10. 17:00填写良品94/总射次100，实际9h；结算填材料成本500元，后端计算成本3200元、毛利1800元、工时偏差-10%，负责人签结后两个实体冻结。若超时到次日08:00，则须负责人确认超时原因；异常偏差或负毛利结算另需复核说明。

V3：09:00 MD-115计划11月25日08:00—12:00顶针润滑与滑块检查，主管批准，完检记回位/模面结果；任何新开工不能回填到该窗口。10:00 RS-P20-DEMO树脂单价20元/kg，为运行试模领30kg；完工退5kg，库存净减25kg、净耗500元，结算材料成本只读500元。11:00签结后交10件样件给华远质量部，记录签收与验收；若卡扣装配需整改，必须再建同模新估单、承诺、开工完工、净耗结算signed后才能绑定关闭。

## 算法口径与限制

输入模腔数、滑块数、重量、钢材编码（P20=0、H13=1、S136=2）。PolynomialFeatures(degree=2, interaction_only=True) 生成原始项和交叉项，StandardScaler 按训练集拟合，Ridge(alpha=3) 回归实际试模工时，本单总预测工时另加准备工时。训练/验证分割固定 42，仅在训练集拟合模型和标准化器；MAE 是留出样本 mean(abs(actual-predicted))。样本少于30失败，预测基础工时下限0.5h。钢材是演示工艺序列编码，扩展无序材料时应改one-hot并重训。

Redis worker结果持久化 Estimate.model_result，同时写 backend/worker 共享命名卷 `/artifacts/estimate-<id>.json`。worker 在取走作业后故障中断的自动重投尚未实现；生产化需可靠队列和恢复机制。时段是人工预算，未实现跨日物理日历或设备停机联动。小型项目没有删除、承诺撤销或财务对接。实际工时按开工/完工时间差计算，未填时区按上海解释，保存UTC。单次最长168h，材料成本由领退料台账计算，单价在领料时冻结；没有停机扣时、工资分摊和多次试模合并。完工实绩没有自动写入训练参考表，基准160条不被暗改。

V3范围：保养时间和客户签收可按演示日期录入，无设备时钟联锁；同模具仅允许一份running实绩。每次试模对同树脂批次只领一次，不提供追加领料或多次退料；批次隔离后的退回库存仍保持隔离。客户样件数按good_shots上界，不另展开一射多腔件数。没有仓库外接、实际物流发送、客户门户或电子签章。

## 本地开发与结构

|层|实现|
|---|---|
|前端|原生 HTML/CSS/JS ES modules、Nginx1.27|
|后端|Python3.12 / FastAPI / SQLAlchemy / PyJWT|
|计算|scikit-learn1.6.1 / NumPy / Redis worker|
|持久化|PostgreSQL16、Redis7 AOF、共享产物卷|

`backend/src/models.py` 类型化模型；`schemas.py` 输入；`services.py` 状态容量事务；`main.py` 路由权限；`ml.py` 模型；`worker.py` 计算；`middlewares.py` 请求ID和突发限流。`backend/scripts/seed_demo.py` 按自然键只增缺失记录，保留用户修改。

V3 `backend/src/workshop_models.py`定义MaintenanceWindow、ResinLot、TrialMaterial、ReviewMaterialLedger、TrialDelivery；`workshop_schemas.py`校验时间、kg、客户记录，`workshop_service.py`负责停机/领耗/交付规则，`workshop_routes.py`提供`/maintenance-windows`、`/resin-lots`、`/trial-materials`、`/trial-deliveries`。原表列无新增，create_all非破坏性增加5张表；新结算另存材料快照凭据，不改旧signed记录。

`backend/src/execution_models.py` 定义实绩/结算外键与唯一约束，`execution_schemas.py` 校验输入，`execution_service.py` 管理快照、工时与成本事务，`execution_routes.py` 暴露 `/executions`、`/cost-reviews` 及 finish/sign 操作。

`frontend/src/pages/` 的 moulds/estimates/evidence/schedule/executions/reviews 及 maintenance/materials/deliveries 是九页；`api.js` HTTP；`store.js` 业务状态；`components/common.js` 状态标签/证据条/选择器跨页复用；`utils/format.js` 转义、金额/数字和表单工具。

本地 `pip install -r backend/requirements.txt`，设置 DATABASE_URL/REDIS_URL，在backend目录 `uvicorn src.main:app --reload`，另一终端 `python -m src.worker`。前端建议使用Compose Nginx代理。

枚举位置：角色、估价状态、实绩状态、结算、保养、树脂、领料、交付状态与钢材定义在 `backend/src/constants.py` 和 `frontend/src/constants.js`；`GET /enums` 返回上述九组。钢材输入Literal在schemas.py、模型编码在ml.py。后端权限为真实约束，前端禁用按钮作提示。IntegrityError转成可恢复409。

环境变量见 `.env.example`：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET、SEED_DEMO。`COMPOSE_SUBNET=10.221.23.0/24` 是本机默认地址池已满后的专用网段；冲突时改空闲网段。数据库、Redis、计算产物为命名卷。

验收脚本、截图、日志在 `../../test-artifacts/gb-1023/`。停止保留数据：`docker compose down`；清理数据：`docker compose down -v --remove-orphans`。

License: MIT。
