"""itscc.kr (IT보안인증사무국) 공지사항/관련규정/자료실 게시판 커스텀 파서.

이 사이트는 목록의 제목이 일반 <a href="..."> 링크가 아니라, JS로 hidden form을
채워서 POST 제출하는 방식(fnDetail())이라 범용 selectors 파서(href 기반)로는
링크를 뽑아낼 수 없다. 대신 상세페이지(/bbs/view.do)가 GET 쿼리스트링도 그대로
받아준다는 것을 확인했으므로, 목록의 <a id="w-85"> 같은 id에서 게시글 번호만
뽑아 "/bbs/view.do?board_id=85&board_class=N&board_lang=KOR" 형태로 직접
링크를 구성한다.

board_class: 1=공지사항, 2=관련규정, 3=자료실 (config/sites.yaml에서 사이트별로 지정)
"""
from bs4 import BeautifulSoup

import crawler

BASE = "https://itscc.kr"


def _view_url(board_id: int, board_class: int) -> str:
    return f"{BASE}/bbs/view.do?board_id={board_id}&board_class={board_class}&board_lang=KOR"


def parse(site_cfg: dict) -> list[dict]:
    board_class = site_cfg["board_class"]
    html = crawler.fetch(site_cfg["list_url"])
    soup = BeautifulSoup(html, "lxml")

    items = []
    for row in soup.select("table.cpl.wideWidth tbody tr"):
        a = row.select_one('a[id^="w-"]')
        tds = row.find_all("td")
        if not a or len(tds) < 3:
            continue

        board_id = int(a["id"].split("-", 1)[1])
        title = a.get_text(strip=True)
        date = tds[2].get_text(strip=True)

        items.append(
            {
                "id": f"class{board_class}-{board_id}",
                "title": title,
                "link": _view_url(board_id, board_class),
                "date": date,
            }
        )
    return items


def check_alive(link: str) -> bool:
    """view.do는 없는 게시글이어도 HTTP 200을 주지만, 제목 <th>가 빈 값으로 온다.
    그걸로 실제 삭제 여부를 판별한다 (직접 확인해서 알아낸 이 사이트만의 특성)."""
    try:
        html = crawler.fetch(link)
    except crawler.CrawlError:
        return False

    soup = BeautifulSoup(html, "lxml")
    title_th = soup.select_one("table.wideWidth thead tr th")
    return bool(title_th and title_th.get_text(strip=True))
