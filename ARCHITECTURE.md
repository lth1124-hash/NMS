# NMS (Notice Monitoring System) 아키텍처 설계

## 1. 목표

정부/기관 공지사항 페이지를 주기적으로 확인하여 **새 글** 또는 **기존 글의 변경**(제목/날짜 등)을
감지하면 이메일로 알려준다. 사이트가 추가/변경되어도 코드를 다시 작성하지 않고
**설정 파일(`config/sites.yaml`)만 수정**하면 되도록 만든다.

## 2. 확정된 조건

| 항목 | 결정 |
|---|---|
| 실행 환경 | GitHub Actions (Public 저장소, 무료·무제한 실행) |
| 스케줄 | 매일 KST 09:00, 18:00 (+ 수동 실행 버튼) |
| 알림 수단 | 이메일 (SMTP, 예: Gmail 앱 비밀번호) |
| 언어 | Python 3.11+ |
| 모니터링 대상 | 미정 → 설정 파일로 확장 가능하게 설계 |

Public 저장소를 쓰므로 `sites.yaml`에는 사이트 이름/URL/CSS 셀렉터만 들어간다.
이 정보는 애초에 공개된 정부 공지사항 페이지 주소이므로 공개되어도 보안 문제가 없다.
계정 정보(SMTP 비밀번호 등)는 저장소에 절대 넣지 않고 **GitHub Secrets**로만 관리한다.

## 3. 폴더 구조

```
NMS/
├── .github/workflows/check_notices.yml   # 스케줄러 (GitHub Actions)
├── config/
│   └── sites.yaml                        # 모니터링 대상 사이트 목록 (사이트 추가 시 여기만 수정)
├── data/
│   └── seen_state.json                   # 마지막으로 확인한 게시물 상태 (자동 갱신, git에 커밋됨)
├── src/
│   ├── main.py                           # 진입점: 전체 흐름 조율
│   ├── crawler.py                        # 사이트 목록 페이지 요청 + 파싱 (설정 기반 범용 파서)
│   ├── differ.py                         # 신규글/변경글 판별
│   ├── notifier.py                       # 이메일 작성/발송
│   ├── state_store.py                    # 상태 파일 읽기/쓰기
│   └── sites/
│       └── _template.py                  # 범용 파서로 안 되는 특이 사이트용 커스텀 파서 템플릿
├── requirements.txt
├── .env.example                          # 로컬 테스트용 환경변수 예시
└── README.md
```

## 4. 데이터 흐름

```
[GitHub Actions cron: 09:00 / 18:00 KST]
        │
        ▼
   main.py 실행
        │
        ├─ config/sites.yaml 로드 (모니터링 대상 목록)
        ├─ data/seen_state.json 로드 (이전에 확인한 상태)
        │
        ├─ 사이트별로 반복 (사이트 하나가 실패해도 나머지는 계속 진행):
        │     ├─ crawler.py → 목록 페이지 요청 + 게시물 목록 추출
        │     │      (title, link, date, 고유 id)
        │     └─ differ.py  → 이전 상태와 비교
        │            ├─ 신규 글 (id가 이전에 없음)
        │            └─ 변경 글 (id는 있는데 title/date 해시가 다름)
        │
        ├─ 신규/변경이 하나라도 있으면 → notifier.py → 이메일 발송
        ├─ data/seen_state.json 갱신
        └─ (workflow에서) 변경된 seen_state.json을 자동 git commit & push
```

## 5. 핵심 컴포넌트

### 5.1 `config/sites.yaml` — 사이트 정의 (확장 포인트)

각 사이트는 목록 페이지의 CSS 셀렉터만 정의하면 된다. 대부분의 정부기관 게시판은
`<table>` 또는 `<ul>` 형태의 목록이라 셀렉터 3~4개로 충분히 커버된다.

```yaml
sites:
  - id: example_agency          # 내부적으로 쓰는 고유 키 (영문/숫자, 상태 저장에 사용)
    name: "예시기관 공지사항"      # 이메일에 표시될 이름
    list_url: "https://example.go.kr/board/notice"
    selectors:
      item: "table.board-list tbody tr"   # 게시물 한 줄(행)을 가리키는 셀렉터
      title: "td.title a"                 # 제목
      link: "td.title a"                  # 링크 (href 속성 사용, 상대경로면 자동으로 절대경로 변환)
      date: "td.date"                     # 날짜 (없으면 생략 가능)
    id_strategy: link      # 게시물을 구분하는 고유값: link | title_date
```

특이 사이트(로그인 필요, JS 렌더링(SPA), API 응답이 JSON인 경우 등)는
`parser: custom`, `module: src.sites.기관명` 형태로 지정하면
`crawler.py`가 해당 모듈의 `parse(html_or_response, base_url) -> list[dict]` 함수를 호출한다.
템플릿은 `src/sites/_template.py`에 있다. **이 부분(사이트별 커스텀 파서, 셀렉터 채우기)이
무료 AI에게 맡기기 좋은 작업이다** — 대상 사이트의 HTML을 보여주고 "위 스키마에 맞춰
selectors 값을 채워줘" 또는 "이 사이트는 JS 렌더링이라 custom parser가 필요해, 아래
템플릿에 맞춰 작성해줘"라고 요청하면 된다.

### 5.2 `src/crawler.py`

- `fetch(url)`: requests로 HTML 가져오기 (timeout, User-Agent 헤더 포함)
- `parse_generic(html, base_url, selectors)`: BeautifulSoup CSS 셀렉터 기반 범용 파싱
- `crawl_site(site_cfg)`: 위 두 함수를 조합, `custom` 파서 지정 시 해당 모듈로 위임
- 반환값: `[{"id": ..., "title": ..., "link": ..., "date": ...}, ...]`

### 5.3 `src/differ.py`

- 이전 상태(`seen_state.json`)의 `{site_id: {item_id: {title, date, hash}}}` 와
  현재 크롤링 결과를 비교
- `id`가 없으면 **신규**, `id`는 있지만 `title+date`의 해시가 다르면 **변경**으로 분류
- 다음 실행을 위한 새 상태 딕셔너리도 함께 생성

### 5.4 `src/notifier.py`

- 신규/변경 항목을 사이트별로 묶어 HTML 이메일 본문 생성
- `smtplib`로 발송 (SMTP 서버/계정 정보는 환경변수로 주입 → GitHub Secrets)
- 발송 대상이 여러 명일 수 있으므로 `NOTIFY_TO`는 콤마로 구분된 리스트 지원

### 5.5 `src/state_store.py`

- `data/seen_state.json` 로드/저장 (파일 없으면 빈 상태로 시작)
- 이 파일은 워크플로우가 끝날 때 자동으로 git commit되어 실행 이력이 남고,
  다음 실행에서도 상태가 유지된다 (GitHub Actions는 매 실행마다 새 컨테이너라
  파일을 커밋해두지 않으면 상태가 사라짐 — Public 저장소를 상태 저장소로 겸용하는 방식).

## 6. 알림 실패/사이트 오류 처리

- 사이트 A 크롤링이 실패해도 사이트 B, C는 계속 진행 (사이트별 `try/except`)
- 실패한 사이트는 로그에 남기고, **실패 자체도 이메일에 별도 섹션("확인 실패")으로 표시**
  → 사이트 구조가 바뀌어서 셀렉터가 깨졌을 때 조용히 놓치는 것을 방지
- 전체 실행이 예외로 죽는 경우는 GitHub Actions 자체가 실패 상태로 표시되고,
  저장소 owner에게 GitHub 기본 알림(이메일)이 감 (추가 설정 없이도 안전망 역할)

## 7. 향후 확장 지점 (지금 당장 구현하지 않음, 구조만 열어둠)

- **알림 수단 추가**: `notifier.py`에 `send_slack()`, `send_teams()` 등을 추가하고
  `main.py`에서 여러 notifier를 리스트로 호출하도록 확장
- **JS 렌더링 사이트**: Playwright 등을 쓰는 custom parser 모듈 추가
- **체크 주기 세분화**: 워크플로우 cron에 트리거를 추가하면 됨 (사이트별로 다른 주기가
  필요해지면 `sites.yaml`에 `schedule_group` 필드를 추가해 필터링하는 방식으로 확장)

## 8. 무료 AI에게 위임할 작업 범위 (제안)

1. 실제 모니터링할 사이트의 목록 페이지 HTML을 보여주고 `sites.yaml` 항목(선택자) 작성 요청
2. 위 항목으로 안 되는 특이 사이트의 `src/sites/기관명.py` 커스텀 파서 작성 요청
3. (선택) 이메일 본문 HTML 템플릿 디자인 개선

핵심 로직(crawler/differ/notifier/state_store, main, workflow yml)은 이미 동작하는
스켈레톤으로 함께 작성해두었으니, 위 3가지 정도만 필요할 때마다 추가하면 된다.
