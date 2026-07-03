# NMS (Notice Monitoring System)

정부/기관 공지사항 페이지를 하루 두 번(KST 09:00, 18:00) 자동으로 확인해서
새 글/변경/삭제를 알려주는 시스템. 현재 itscc.kr(공지사항/관련규정/자료실)을 모니터링 중.

전체 설계 배경과 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md) 참고.

## 1. 로컬에서 테스트하기

```bash
pip install -r requirements.txt

# .env.example 참고. ntfy.sh만 쓸 거면 이거 하나면 충분:
export NTFY_TOPIC=nms-itscc-여기에_무작위_문자열

cd src
python main.py
```

## 2. 알림 받기 설정 (ntfy.sh - 가입 불필요, 추천)

1. 남이 못 알아챌 정도로 무작위 문자열이 섞인 토픽 이름을 정한다. (예: `nms-itscc-a1f12612`)
2. 휴대폰에 **ntfy** 앱 설치(App Store / Play Store) → 그 토픽 이름으로 구독(Subscribe)
3. GitHub 저장소 Settings → Secrets and variables → Actions → New repository secret
   - `NTFY_TOPIC` = 위에서 정한 토픽 이름
4. 끝. 이제부터 새 글/변경/삭제가 감지되면 휴대폰으로 푸시 알림이 온다.

이메일(SMTP)도 같이 쓰고 싶으면 `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASS`/`NOTIFY_TO`
Secret도 추가로 등록하면 된다 (`.env.example` 참고). 둘 다 등록하면 ntfy + 이메일 둘 다 온다.

## 3. 모니터링할 사이트 추가하기

1. 대상 공지사항 목록 페이지를 브라우저에서 열고, 개발자도구(F12) → Elements 탭에서
   게시물 목록의 HTML 구조를 확인한다 (표 형태인지, `<ul><li>` 형태인지 등).
2. `config/sites.yaml`에 사이트 블록을 추가한다 (파일 안의 작성 예시 참고).
   - `item`: 게시물 한 줄(행)을 가리키는 CSS 셀렉터
   - `title`, `link`, `date`: 각각 제목/링크/날짜 요소의 셀렉터
3. **셀렉터 작성이 어려우면 무료 AI(ChatGPT 등)에게 맡겨도 된다** — 해당 사이트의
   목록 페이지 HTML 일부를 복사해서 "아래 YAML 스키마에 맞춰 selectors 값을 채워줘"라고
   요청하면 된다. (`config/sites.yaml` 상단 주석에 스키마 설명이 있으니 그대로 붙여넣으면 됨)
4. 로컬에서 `python src/main.py`로 먼저 테스트해보고 신규 항목이 잘 잡히는지 확인한다.
5. 정상 동작하면 git commit & push. 다음 스케줄 실행부터 자동으로 포함된다.

### JS로 렌더링되는 사이트(SPA)나 itscc.kr처럼 링크가 href가 아닌 경우

`src/sites/_template.py`를 복사해서 커스텀 파서를 작성한다 (`src/sites/itscc.py`가 실제 예시).
대부분은 화면이 JS로 그려져도 내부적으로는 JSON을 반환하는 API를 호출하고 있으므로,
브라우저 개발자도구의 Network 탭에서 그 API 요청을 찾아 직접 호출하는 방식이 Playwright
같은 무거운 도구보다 훨씬 간단하다. 이런 사이트는 무료 AI에게 "이 API 응답 예시(JSON)를
보고 파서를 작성해줘"라고 요청하기 좋다.

## 4. 폴더 구조

```
config/sites.yaml     모니터링 대상 사이트 목록 (여기만 수정하면 사이트 추가 가능)
src/main.py           진입점
src/crawler.py        목록 페이지 요청 + 파싱 + 삭제 확인
src/differ.py         신규/변경/삭제후보 판별
src/notifier.py       ntfy/이메일 알림 발송 (설정된 것 전부에 보냄)
src/state_store.py    상태 파일(data/seen_state.json) 읽기/쓰기
src/sites/itscc.py    itscc.kr 전용 커스텀 파서
src/sites/_template.py  새 사이트용 커스텀 파서 템플릿
.github/workflows/check_notices.yml  스케줄러 (매일 KST 09:00/18:00)
```
