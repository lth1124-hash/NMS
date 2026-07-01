"""현재 크롤링 결과와 이전 상태(state)를 비교해 신규/변경/(잠재적)삭제 게시물을 뽑아낸다.

주의: 목록 페이지는 최신 N건만 보여주므로, 이전에 있던 글이 이번 크롤링 결과에
없다고 해서 바로 "삭제됨"으로 확정하면 안 된다 (새 글이 쌓여서 페이지 밖으로
밀려난 것일 수도 있음). 그래서 여기서는 "missing_ids"(사라진 후보)만 뽑아주고,
실제 삭제 여부 확인(해당 게시물 링크에 다시 접속해보는 것)은 main.py에서
crawler.check_alive()로 한 번 더 확인한다.
"""
import hashlib


def _content_hash(title: str, date: str) -> str:
    return hashlib.sha256(f"{title}|{date}".encode("utf-8")).hexdigest()


def diff_site(site_id: str, current_items: list[dict], state: dict) -> tuple[list[dict], list[dict], set, dict]:
    """returns (new_items, updated_items, missing_ids, new_site_state)"""
    prev = state.get(site_id, {})
    new_items = []
    updated_items = []
    new_site_state = {}

    for item in current_items:
        item_id = item["id"]
        h = _content_hash(item["title"], item["date"])
        new_site_state[item_id] = {
            "title": item["title"],
            "date": item["date"],
            "link": item["link"],
            "hash": h,
        }

        prev_entry = prev.get(item_id)
        if prev_entry is None:
            new_items.append(item)
        elif prev_entry.get("hash") != h:
            updated_items.append(item)

    current_ids = {item["id"] for item in current_items}
    missing_ids = set(prev.keys()) - current_ids

    return new_items, updated_items, missing_ids, new_site_state
