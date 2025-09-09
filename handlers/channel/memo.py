"""
チャンネルメモ機能
"""

from typing import Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime
import re

from db.repository import (
    search_channel_memos,
    get_channel_memo_stats,
    get_recent_channel_memos
)


def parse_datetime_safely(datetime_str: str) -> datetime:
    """安全に日時文字列をパースする"""
    try:
        # 基本的なISO形式のパース
        clean_str = datetime_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except ValueError:
        try:
            # マイクロ秒の桁数を調整して再試行
            if '.' in clean_str and '+' in clean_str:
                date_part, time_and_tz = clean_str.split('T')
                time_part, tz_part = time_and_tz.rsplit('+', 1)
                if '.' in time_part:
                    time_base, microseconds = time_part.split('.')
                    # マイクロ秒を6桁に調整
                    microseconds = microseconds.ljust(6, '0')[:6]
                    clean_str = f"{date_part}T{time_base}.{microseconds}+{tz_part}"
                return datetime.fromisoformat(clean_str)
        except:
            pass

        # 最終的にフォールバック（現在時刻を返す）
        return datetime.now()


def create_memo_search_input_blocks() -> list[Dict[str, Any]]:
    """メモ検索入力フォーム用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🔍 メモ検索"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "検索したいキーワードを入力してください："
            }
        },
        {
            "type": "input",
            "block_id": "search_input_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "search_input",
                "placeholder": {
                    "type": "plain_text",
                    "text": "例: 会議、プロジェクト、TODO..."
                }
            },
            "label": {
                "type": "plain_text",
                "text": "検索キーワード"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔍 検索実行"
                    },
                    "style": "primary",
                    "action_id": "execute_memo_search"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔙 メニューに戻る"
                    },
                    "action_id": "show_channel_menu"
                }
            ]
        }
    ]


def create_search_result_blocks(memos: List[Dict], keyword: str) -> list[Dict[str, Any]]:
    """検索結果表示用のブロックを作成"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 検索結果: {keyword}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{len(memos)}件* のメモが見つかりました"
            }
        },
        {
            "type": "divider"
        }
    ]

    for memo in memos:
        created_at = parse_datetime_safely(memo['created_at'])
        formatted_date = created_at.strftime('%Y-%m-%d %H:%M')

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{formatted_date}*\n{memo['message'][:200]}{'...' if len(memo['message']) > 200 else ''}"
            }
        })
        blocks.append({"type": "divider"})

    # 戻るボタン
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔙 メニューに戻る"
                },
                "action_id": "show_channel_menu"
            }
        ]
    })

    return blocks


def create_memo_stats_blocks(stats: Dict) -> list[Dict[str, Any]]:
    """メモ統計表示用のブロックを作成（ユーザーランキング含む）"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📊 メモ統計"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*総メモ数*\n{stats.get('total_memos', 0):,}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*今日のメモ*\n{stats.get('today_memos', 0):,}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*今週のメモ*\n{stats.get('week_memos', 0):,}件"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*今月のメモ*\n{stats.get('month_memos', 0):,}件"
                }
            ]
        }
    ]

    # アクティブユーザーランキングを追加
    if 'user_rankings' in stats and stats['user_rankings']:
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📈 アクティブユーザーランキング"
            }
        })

        ranking_text = ""
        for i, user_stat in enumerate(stats['user_rankings'][:10], 1):  # 上位10位まで
            user_id = user_stat.get('user_id', '不明')
            memo_count = user_stat.get('memo_count', 0)

            # ランキング絵文字
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."

            ranking_text += f"{emoji} <@{user_id}> - {memo_count}件\n"

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ranking_text.strip()
            }
        })

    # 戻るボタン
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔙 メニューに戻る"
                },
                "action_id": "show_channel_menu"
            }
        ]
    })

    return blocks


def create_recent_memos_blocks(memos: List[Dict]) -> list[Dict[str, Any]]:
    """最近のメモ表示用のブロックを作成"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 最近のメモ"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"最新の *{len(memos)}件* のメモを表示しています"
            }
        },
        {
            "type": "divider"
        }
    ]

    for memo in memos:
        created_at = parse_datetime_safely(memo['created_at'])
        formatted_date = created_at.strftime('%Y-%m-%d %H:%M')

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{formatted_date}* - <@{memo['user_id']}>\n{memo['content'][:150]}{'...' if len(memo['content']) > 150 else ''}"
            }
        })
        blocks.append({"type": "divider"})

    # 戻るボタン
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔙 メニューに戻る"
                },
                "action_id": "show_channel_menu"
            }
        ]
    })

    return blocks


def create_memo_list_blocks(memos: List[Dict[str, Any]], page: int = 1) -> list[Dict[str, Any]]:
    """メモ一覧表示用のブロックを作成"""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 メモ一覧"
            }
        }
    ]

    if not memos:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "   メモが見つかりませんでした。"
            }
        })
    else:
        # メモの数を表示
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*全{len(memos)}件のメモ*"
            }
        })

        # 各メモを表示
        for i, memo in enumerate(memos[:30], 1):  # 最初の30件のみ表示
            created_at = parse_datetime_safely(memo["created_at"])
            jst_time = created_at.astimezone().strftime("%m/%d %H:%M")

            memo_text = memo["message"]
            if len(memo_text) > 150:
                memo_text = memo_text[:150] + "..."

            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{i}. {memo['user_name']}* ({jst_time})\n{memo_text}"
                },
                "accessory": {
                    "type": "overflow",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "✏️ 編集"
                            },
                            "value": f"edit_memo_{memo['id']}"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "🗑️ 削除"
                            },
                            "value": f"delete_memo_{memo['id']}"
                        }
                    ],
                    "action_id": f"memo_actions_{memo['id']}"
                }
            }

            # 元メッセージへのリンクがある場合は追加
            if memo.get("permalink"):
                block["accessory"]["options"].insert(0, {
                    "text": {
                        "type": "plain_text",
                        "text": "🔗 元メッセージ"
                    },
                    "url": memo["permalink"]
                })

            blocks.append(block)

        # 30件以上ある場合の注意書き
        if len(memos) > 30:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"💡 最新30件のみ表示しています。（全{len(memos)}件）"
                    }
                ]
            })

    # メニューに戻るボタン
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔙 メニューに戻る"
                },
                "action_id": "show_channel_menu"
            }
        ]
    })

    return blocks


def create_memo_edit_modal_blocks(memo: Dict[str, Any]) -> list[Dict[str, Any]]:
    """メモ編集モーダル用のブロックを作成"""
    return [
        {
            "type": "input",
            "block_id": "memo_text_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "memo_text_input",
                "multiline": True,
                "initial_value": memo["message"],
                "max_length": 1000
            },
            "label": {
                "type": "plain_text",
                "text": "メモ内容"
            }
        }
    ]


def create_memo_create_form_blocks() -> list[Dict[str, Any]]:
    """メモ作成フォーム用のブロックを作成"""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 メモ作成"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "新しいメモを作成します。メモ内容を入力してください："
            }
        },
        {
            "type": "input",
            "block_id": "memo_content_block",
            "element": {
                "type": "plain_text_input",
                "action_id": "memo_content_input",
                "multiline": True,
                "placeholder": {
                    "type": "plain_text",
                    "text": "例: 会議資料の確認..."
                },
                "max_length": 1000
            },
            "label": {
                "type": "plain_text",
                "text": "メモ内容"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "📝 メモを作成"
                    },
                    "style": "primary",
                    "action_id": "execute_memo_create"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "🔙 メニューに戻る"
                    },
                    "action_id": "show_channel_menu"
                }
            ]
        }
    ]
