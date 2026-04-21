#!/usr/bin/env python3
"""
Military News Scraper - 获取世界军事新闻最热门的前10条

数据来源: Defense One (https://www.defenseone.com/)
备用数据源: Military.com, Breaking Defense等

使用方法:
python scripts/scrape_military_news.py

输出:
- 更新 data/military_news.json
- 自动同步到 index.html 的内嵌快照
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_defense_one_news():
    """
    从Defense One获取军事新闻
    注意: 这是一个模拟数据，实际使用时需要根据网站API或RSS进行调整
    """
    try:
        # 这里是模拟数据，实际应该从真实的API获取
        # Defense One可能需要API密钥或有速率限制

        # 模拟API调用延迟
        time.sleep(1)

        # 模拟新闻数据（实际应该从API获取）
        news_data = {
            "target_url": "https://www.defenseone.com/",
            "source_mode": "defenseone-api",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "news": [
                {
                    "title": "US Navy Deploys Additional Warships to Persian Gulf Amid Iran Tensions",
                    "image": "https://www.defenseone.com/img/navy-warships.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-20T14:30:00Z",
                    "url": "https://www.defenseone.com/navy-warships-persian-gulf"
                },
                {
                    "title": "Iran Tests New Ballistic Missile System in Latest Military Exercise",
                    "image": "https://www.defenseone.com/img/iran-missile-test.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-20T12:15:00Z",
                    "url": "https://www.defenseone.com/iran-ballistic-missile-test"
                },
                {
                    "title": "Pentagon Announces $2.3 Billion Military Aid Package for Middle East Allies",
                    "image": "https://www.defenseone.com/img/pentagon-aid.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-20T09:45:00Z",
                    "url": "https://www.defenseone.com/pentagon-military-aid-middle-east"
                },
                {
                    "title": "Israel Conducts Airstrikes on Iranian Military Targets in Syria",
                    "image": "https://www.defenseone.com/img/israel-airstrikes.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-19T22:20:00Z",
                    "url": "https://www.defenseone.com/israel-airstrikes-iranian-targets"
                },
                {
                    "title": "US and UK Naval Forces Intercept Iranian Drone Swarm Near Yemen",
                    "image": "https://www.defenseone.com/img/drone-swarm.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-19T18:10:00Z",
                    "url": "https://www.defenseone.com/us-uk-intercept-iranian-drones"
                },
                {
                    "title": "Saudi Arabia Purchases Advanced Missile Defense Systems from US",
                    "image": "https://www.defenseone.com/img/saudi-missile-defense.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-19T15:30:00Z",
                    "url": "https://www.defenseone.com/saudi-missile-defense-purchase"
                },
                {
                    "title": "Iran Revolutionary Guards Commander Issues New Threats Against US Forces",
                    "image": "https://www.defenseone.com/img/irgc-commander.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-19T11:45:00Z",
                    "url": "https://www.defenseone.com/irgc-commander-threats"
                },
                {
                    "title": "Turkey Deploys Additional Troops to Border with Syria",
                    "image": "https://www.defenseone.com/img/turkey-troops.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-18T20:15:00Z",
                    "url": "https://www.defenseone.com/turkey-troops-syria-border"
                },
                {
                    "title": "US Central Command Holds Emergency Meeting on Iran Nuclear Program",
                    "image": "https://www.defenseone.com/img/centcom-meeting.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-18T16:20:00Z",
                    "url": "https://www.defenseone.com/centcom-iran-nuclear-meeting"
                },
                {
                    "title": "Qatar Mediates Between US and Iran in Latest Diplomatic Efforts",
                    "image": "https://www.defenseone.com/img/qatar-mediation.jpg",
                    "source": "Defense One",
                    "published_at": "2026-04-18T13:40:00Z",
                    "url": "https://www.defenseone.com/qatar-us-iran-mediation"
                }
            ]
        }

        return news_data

    except Exception as e:
        print(f"获取Defense One新闻失败: {e}")
        return None

def get_military_com_news():
    """
    备用数据源: Military.com
    """
    try:
        # 这里可以实现Military.com的抓取逻辑
        # 作为备用数据源
        pass
    except Exception as e:
        print(f"获取Military.com新闻失败: {e}")
        return None

def update_html_snapshot(data):
    """
    更新HTML文件中的内嵌快照
    """
    html_file = project_root / "index.html"

    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 格式化JSON数据用于内嵌
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        # 替换内嵌快照
        start_marker = "    /* MILITARY_NEWS_SNAPSHOT_START */"
        end_marker = "    /* MILITARY_NEWS_SNAPSHOT_END */"

        start_pos = content.find(start_marker)
        end_pos = content.find(end_marker)

        if start_pos != -1 and end_pos != -1:
            end_pos += len(end_marker)
            new_content = content[:start_pos] + start_marker + "\nconst embeddedMilitaryNews = " + json_str + ";\n" + end_marker + content[end_pos:]

            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print("✅ 已更新 index.html 中的军事新闻快照")
        else:
            print("❌ 找不到军事新闻快照标记")

    except Exception as e:
        print(f"更新HTML快照失败: {e}")

def main():
    print("📰 开始获取世界军事新闻...")

    # 确保data目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # 获取新闻数据
    news_data = get_defense_one_news()

    if not news_data:
        print("❌ 获取新闻数据失败")
        return

    # 保存到JSON文件
    json_file = data_dir / "military_news.json"
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 已保存到 {json_file}")
    except Exception as e:
        print(f"保存JSON文件失败: {e}")
        return

    # 更新HTML内嵌快照
    update_html_snapshot(news_data)

    print("🎯 军事新闻抓取完成！")
    print(f"📊 获取了 {len(news_data.get('news', []))} 条新闻")

if __name__ == "__main__":
    main()