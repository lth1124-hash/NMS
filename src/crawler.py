"""사이트 설정(config/sites.yaml)을 기반으로 공지사항 목록을 가져와 파싱한다.

대부분의 정부기관 게시판(표/리스트 형태 정적 HTML)은 selectors 몇 개로 커버되고,
그렇지 않은 특이 사이트는 parser: custom 으로 src/sites/ 아래 모듈에 위임한다.
"""
import hashlib
import importlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "NMS-NoticeMonitoringBot/1.0 (+internal use)"
    )
}


class CrawlError(Exception):
    pass


def fetch(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except requests.RequestException as e:
        raise CrawlError(f"요청 실패: {url} ({e})") from e


def _make_id(link: str, title: str, date: str, id_strategy: str) -> str:
    if id_strategy == "title_date":
        raw = f"{title}|{date}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return link  # default: link


def parse_generic(html: str, base_url: str, selectors: dict, id_strategy: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for el in soup.select(selectors["item"]):
        title_el = el.select_one(selectors["title"])
        link_el = el.select_one(selectors.get("link", selectors["title"]))
        date_el = el.select_one(selectors["date"]) if selectors.get("date") else None

        if not title_el or not link_el:
            continue

        title = title_el.get_text(strip=True)
        href = link_el.get("href", "").strip()
        if not href:
            continue
        link = urljoin(base_url, href)
        date = date_el.get_text(strip=True) if date_el else ""

        item_id = _make_id(link, title, date, id_strategy)
        items.append({"id": item_id, "title": title, "link": link, "date": date})
    return items


def crawl_site(site_cfg: dict) -> list[dict]:
    if site_cfg.get("parser") == "custom":
        # module 예: "sites.example_agency" (src/sites/example_agency.py)
        module_path = site_cfg["module"]
        module = importlib.import_module(module_path)
        return module.parse(site_cfg)

    html = fetch(site_cfg["list_url"])
    return parse_generic(
        html,
        base_url=site_cfg["list_url"],
        selectors=site_cfg["selectors"],
        id_strategy=site_cfg.get("id_strategy", "link"),
    )


def check_alive(site_cfg: dict, link: str) -> bool:
    """목록에서 사라진 게시물이 진짜 삭제된 건지 확인한다.

    custom 파서를 쓰는 사이트는 detail 페이지 구조를 알고 있으므로 그 사이트
    모듈에 check_alive(link)가 있으면 그걸 우선 쓴다. 없으면 기본적으로는
    "링크에 정상 접속되면 살아있다"로 간주한다 (일부 CMS는 없는 글도 200을
    주는 경우가 있어 완벽하지 않을 수 있음 - 그런 사이트는 custom 모듈에
    check_alive를 직접 구현해서 정확도를 높인다).
    """
    if site_cfg.get("parser") == "custom":
        module = importlib.import_module(site_cfg["module"])
        custom_check = getattr(module, "check_alive", None)
        if custom_check is not None:
            return custom_check(link)

    try:
        fetch(link)
        return True
    except CrawlError:
        return False
