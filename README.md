# Iran-monitor-mini

一个可直接本地打开的单页仪表盘，聚合展示：
- 冲突状态与提示
- Polymarket 相关市场
- 宏观资产价格（原油、黄金、标普500、美国10Y）
- BCA 摘要内容

## 项目结构

```text
Iran-monitor-mini/
├─ index.html
├─ scripts/
│  ├─ scrape_bca_dashboard.py
│  ├─ scrape_polymarket_markets.py
│  └─ scrape_macro_assets.py
├─ data/
│  ├─ bca_dc_description.json
│  ├─ polymarket_footer_markets.json
│  └─ macro_assets.json
├─ .gitignore
└─ README.md
```

## 使用方式

1. 打开网页：直接双击 `index.html`
2. 刷新 BCA 数据：
```bash
python scripts/scrape_bca_dashboard.py
```
3. 刷新 Polymarket footerData：
```bash
python scripts/scrape_polymarket_markets.py
```
4. 刷新宏观资产价格：
```bash
python scripts/scrape_macro_assets.py
```

运行脚本后会自动更新 `data/*.json`，并同步写入 `index.html` 的内嵌快照。

## 数据来源

- BCA: https://www.bcaresearch.com/collection/bcas-iran-conflict-daily-dashboard
- Polymarket: https://polymarket.com/zh
- 宏观资产: https://stooq.com/ + https://fred.stlouisfed.org/

## 开发说明

- 建议 Python 3.11+
- 当前脚本主要依赖 Python 标准库，可直接运行
- 页面内置每 1 小时自动刷新（前端定时整页 reload）
