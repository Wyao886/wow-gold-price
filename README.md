# 魔兽世界时光服金价云端采集

每 6 小时自动采集 7881 平台 · 魔兽世界时光服 · 1区(时光I PvE) · 部落 金币价格，
结果写入 `gold_price_history.csv`（北京时间）。

- 采集脚本：`gold_cloud.py`（纯 Python 标准库）
- 定时任务：GitHub Actions，北京时间 **07:09 / 12:09 / 18:09** 各一次
  （GitHub 定时任务可能延迟 0~30 分钟属正常现象）

## 数据列说明

| 列 | 含义 |
|---|---|
| datetime | 采集时间（北京时间） |
| horde_listings / total_listings | 部落挂单数 / 总挂单数 |
| min_yuan_per_10k | 实时最低挂单价（元/万金） |
| avg_yuan_per_10k | 全部部落挂单均价 |
| avg_top10_yuan_per_10k | 前十低价挂单均价 |
| median_yuan_per_10k | 中位数 |
| recycle_max_yuan_per_10k | 回收最高价（元/万金） |
| recycle_avg3_yuan_per_10k | 回收前三均价 |

## 手动触发

Actions 页面 → 左侧 "Gold Price Collector" → 右上角 "Run workflow"。
