# 稳盈量化 V1.0 · 第一阶段（可运行研究版）

**状态：已实现基础行情校验、CSV数据导入、简单强趋势候选筛选、模拟回测与测试；尚未实现七策略、完整市场风格判断、30分钟回测和全A股历史数据库。** 不保证稳定盈利。

## 从零安装（Codex 云端终端 / Linux / macOS / Windows PowerShell）

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install -e '.[test]'
python -m pytest -q
python -m wenying.cli validate --input data/demo.csv
python -m wenying.cli screen --input data/demo.csv
python -m wenying.cli backtest --input data/demo.csv
```

生成 `outputs/candidates.csv`、`outputs/equity.csv`、`outputs/trades.csv`、`outputs/summary.json`。

## 数据格式

CSV列：`date,symbol,open,high,low,close,volume`，date=YYYY-MM-DD；symbol为六位股票代码。使用一致口径的价格序列；**实际成交价格不能直接用后复权价格**，本阶段使用示例研究数据，不可直接推断实盘执行价格。真实行情接入前需补齐复权因子、历史ST状态、涨跌停价格、交易日历、退市股、停牌与可成交性判断。

## 可选：下载少量真实日线（需网络）

```bash
python -m pip install -e '.[data]'
python -c "from wenying.download import download_daily; print(download_daily(['000001','600519']))"
```

`data/raw/*.csv` 为单股CSV；下载接口不承诺历史完整性，需校验覆盖率。不要把接口实时抓取当成已下载五年全A股。30分钟历史免费源往往覆盖不足，不能假定可取得完整五年。

## 回测假设与已知缺陷

- t日收盘形成信号，t+1开盘买入；仅100股整数手，最多20%资金单票；初始资金10万元。
- 持有最多3个交易日后产生退出信号，**下一交易日开盘**退出，实际可持有超过3天；收盘跌破5%止损也仅下一交易日开盘卖出。
- 双边佣金0.03%、最低5元，卖出印花税示例0.05%、单边滑点0.1%，仅研究默认值，历史费率须按日期校准。
- 月度从高点回撤5%暂停新开仓；连续3笔亏损暂停新开仓，需后续加入复位机制。
- 目前未模拟真实涨跌停不可成交、涨停封单、开盘停牌、复权与公司行动、指数成分历史变化、涨跌幅制度差异、分红、融资融券、冲击成本。回测结果仅演示软件流程。
- 策略规则为开发者**自行构造的强趋势代理**，不是手册提供的完整公式；手册指出交易模式需结合市场风格，七类策略未提供完整公式。

## 下一阶段

1. 数据层：股票历史名单+日线分区Parquet+30分钟可用性报告+数据质量检查。
2. 执行层：逐日市场状态、真实涨跌停约束、T+1与停牌、动态成本。
3. 策略层：强趋势、板块轮动、龙头分歧三模块及样本外滚动回测。
4. 账户层：每日/月度净值、回撤与连亏、风险预算、可配置复位。

## Codex 提示词

请在此仓库基础上继续开发，先运行 pytest 并修复所有失败。保持无未来数据泄漏；实现历史A股证券主数据和行情数据完整性验证；使用可替换数据源适配器、增量下载、断点续传、失败重试与日志；将复权行情与实际成交价格分离；完善涨跌停、停牌、T+1交易约束；为每一项假设编写测试；不要声称盈利能力，只有样本外回测通过后才展示统计指标。不要删除现有可运行命令。
