"""범용 파서(config/sites.yaml의 selectors)로 처리되지 않는 특이 사이트용 커스텀 파서 템플릿.

사용법:
  1. 이 파일을 src/sites/기관명.py 로 복사
  2. config/sites.yaml에서 해당 사이트에 parser: custom, module: sites.기관명 지정
  3. 아래 parse() 함수를 실제 사이트에 맞게 구현

흔한 특이 케이스:
  - 로그인/세션이 필요한 게시판 → requests.Session()으로 로그인 후 목록 요청
  - 목록이 JS로 렌더링되는 SPA → 실제로는 내부적으로 JSON API를 호출하는 경우가 많으니
    브라우저 개발자도구(Network 탭)에서 XHR 요청을 찾아 그 API를 직접 호출하는 편이
    Playwright 같은 무거운 렌더러보다 훨씬 가볍고 안정적이다.
  - 페이지네이션이 있는 경우 → 최근 N페이지만 확인하도록 제한 (전체 이력은 필요 없음)
"""


def parse(site_cfg: dict) -> list[dict]:
    """
    Args:
        site_cfg: config/sites.yaml에 정의된 해당 사이트의 설정 딕셔너리 전체
                  (list_url 등 필요한 값을 여기서 꺼내 쓴다)

    Returns:
        각 게시물을 나타내는 dict의 리스트. 각 dict는 반드시 아래 키를 포함해야 한다:
          - id:    게시물 고유 식별자 (보통 절대 URL을 그대로 쓰면 충분)
          - title: 제목
          - link:  절대 URL
          - date:  날짜 문자열 (없으면 "")
    """
    raise NotImplementedError(
        f"{site_cfg.get('id')}용 커스텀 파서가 아직 구현되지 않았습니다. "
        "이 함수를 실제 사이트에 맞게 작성하세요."
    )
