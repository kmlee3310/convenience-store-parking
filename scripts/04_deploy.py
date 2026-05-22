"""
scripts/04_deploy.py  — convenience-store-parking 專案

人有三急版本完全相同的部署邏輯，此專案無需額外調整。
執行順序（FK 約束保證）：
  store 新增 → store 修改 → store_service 新增 → store_service 刪除 → store 刪除
"""

import os
import json
from supabase import create_client
from datetime import datetime

# ============================================================
# 設定
# ============================================================
PAYLOAD_PATH = "diff_payload/diff.json"
BATCH_SIZE   = 500
TIMESTAMP    = datetime.now().strftime("%Y%m%d%H%M")

# ============================================================
# Supabase client
# ============================================================
def get_client():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )


def batched(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ============================================================
# 部署函式
# ============================================================
def deploy_store_insert(supabase, records):
    print(f"\n[store] 新增 {len(records)} 筆...")
    for i, batch in enumerate(batched(records, BATCH_SIZE)):
        supabase.table("store").insert(batch).execute()
        print(f"  批次 {i+1}：寫入 {len(batch)} 筆")
    print("  ✅ store 新增完成")


def deploy_store_update(supabase, records):
    print(f"\n[store] 修改 {len(records)} 筆...")
    for item in records:
        update_data = {col: v["new"] for col, v in item["changes"].items()}
        supabase.table("store").update(update_data).eq("store_id", item["store_id"]).execute()
    print("  ✅ store 修改完成")


def deploy_store_delete(supabase, records):
    print(f"\n[store] 刪除 {len(records)} 筆...")
    ids = [r["store_id"] for r in records]
    for batch in batched(ids, BATCH_SIZE):
        supabase.table("store").delete().in_("store_id", batch).execute()
    print("  ✅ store 刪除完成")


def deploy_svc_insert(supabase, records):
    print(f"\n[store_service] 新增 {len(records)} 筆（停車場）...")
    for i, batch in enumerate(batched(records, BATCH_SIZE)):
        supabase.table("store_service").insert(batch).execute()
        print(f"  批次 {i+1}：寫入 {len(batch)} 筆")
    print("  ✅ store_service 新增完成")


def deploy_svc_delete(supabase, records):
    print(f"\n[store_service] 刪除 {len(records)} 筆（停車場）...")
    for r in records:
        supabase.table("store_service").delete()\
            .eq("store_id", r["store_id"])\
            .eq("service_id", r["service_id"])\
            .execute()
    print("  ✅ store_service 刪除完成")


# ============================================================
# 部署結果寫入 Summary
# ============================================================
def write_deploy_summary(payload, success=True, error_msg=None):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "/tmp/summary.md")
    lines = []
    lines.append("# 🚀 停車場門市部署結果報告\n")
    lines.append(f"> 執行時間：{TIMESTAMP}  |  來源資料時間戳：{payload.get('timestamp', 'N/A')}\n")

    if success:
        lines.append("## ✅ 部署成功！\n")
        lines.append("| 資料表 | 操作 | 筆數 |")
        lines.append("|--------|------|------|")
        lines.append(f"| `store` | 新增 | {len(payload['store_insert'])} |")
        lines.append(f"| `store` | 修改 | {len(payload['store_update'])} |")
        lines.append(f"| `store` | 刪除 | {len(payload['store_delete'])} |")
        lines.append(f"| `store_service` | 新增 | {len(payload['svc_insert'])} |")
        lines.append(f"| `store_service` | 刪除 | {len(payload['svc_delete'])} |")
    else:
        lines.append("## ❌ 部署失敗\n")
        lines.append(f"```\n{error_msg}\n```")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ============================================================
# 主程式
# ============================================================
def main():
    print(f"{'='*50}")
    print(f"04_deploy.py 開始執行：{TIMESTAMP}")
    print(f"{'='*50}")

    if not os.path.exists(PAYLOAD_PATH):
        raise FileNotFoundError(f"找不到 diff payload：{PAYLOAD_PATH}")

    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    store_insert = payload["store_insert"]
    store_update = payload["store_update"]
    store_delete = payload["store_delete"]
    svc_insert   = payload["svc_insert"]
    svc_delete   = payload["svc_delete"]

    total = len(store_insert) + len(store_update) + len(store_delete) + len(svc_insert) + len(svc_delete)
    print(f"  store     → 新增 {len(store_insert)}，修改 {len(store_update)}，刪除 {len(store_delete)}")
    print(f"  svc       → 新增 {len(svc_insert)}，刪除 {len(svc_delete)}")
    print(f"  總異動筆數：{total}")

    supabase = get_client()

    try:
        if store_insert:
            deploy_store_insert(supabase, store_insert)
        if store_update:
            deploy_store_update(supabase, store_update)
        if svc_insert:
            deploy_svc_insert(supabase, svc_insert)
        if svc_delete:
            deploy_svc_delete(supabase, svc_delete)
        if store_delete:
            deploy_store_delete(supabase, store_delete)

        print(f"\n🎉 全部部署完成！共處理 {total} 筆異動")
        write_deploy_summary(payload, success=True)

    except Exception as e:
        print(f"\n❌ 部署失敗：{e}")
        write_deploy_summary(payload, success=False, error_msg=str(e))
        raise


if __name__ == "__main__":
    main()

