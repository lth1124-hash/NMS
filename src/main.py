"""NMS 진입점: 설정된 모든 사이트를 순회하며 신규/변경/삭제 게시물을 감지하고 알린다.

실행: 프로젝트 루트에서 `python src/main.py`
(스크립트를 직접 실행하면 파이썬이 src/ 폴더를 자동으로 sys.path에 넣어주므로
 같은 폴더의 crawler/differ/notifier/state_store를 바로 import할 수 있다)
"""
from pathlib import Path

import yaml

import crawler
import differ
import notifier
import state_store

SITES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sites.yaml"


def load_sites(path: Path = SITES_CONFIG_PATH) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("sites") or []


def main() -> int:
    sites = load_sites()
    if not sites:
        print("설정된 사이트가 없습니다 (config/sites.yaml). 종료합니다.")
        return 0

    state = state_store.load_state()
    results = []
    failures = []

    for site in sites:
        site_id = site["id"]
        try:
            current_items = crawler.crawl_site(site)
        except Exception as e:  # noqa: BLE001 - 사이트 하나 실패해도 나머지는 계속
            print(f"[ERROR] {site_id}: {e}")
            failures.append({"site_name": site.get("name", site_id), "error": str(e)})
            continue

        prev_site_state = state.get(site_id, {})
        new_items, updated_items, missing_ids, new_site_state = differ.diff_site(
            site_id, current_items, state
        )

        # 목록에서 사라진 게시물 후보(missing_ids) 하나씩, 실제로 삭제된 건지
        # 링크에 다시 접속해서 확인한다. 살아있으면(=페이지 밖으로 밀려난 것)
        # 상태에 그대로 남겨서 계속 추적하고, 죽었으면(=진짜 삭제) 알림 대상에 넣는다.
        deleted_items = []
        for missing_id in missing_ids:
            entry = prev_site_state[missing_id]
            if crawler.check_alive(site, entry["link"]):
                new_site_state[missing_id] = entry
            else:
                deleted_items.append({"title": entry["title"], "date": entry.get("date", ""), "link": entry["link"]})

        state[site_id] = new_site_state

        results.append(
            {
                "site_id": site_id,
                "site_name": site.get("name", site_id),
                "new_items": new_items,
                "updated_items": updated_items,
                "deleted_items": deleted_items,
            }
        )
        print(
            f"[OK] {site_id}: 신규 {len(new_items)}건, 변경 {len(updated_items)}건, "
            f"삭제 {len(deleted_items)}건"
        )

    if notifier.has_notifiable_content(results, failures):
        notifier.send_all(results, failures)
    else:
        print("알릴 내용 없음")

    state_store.save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
