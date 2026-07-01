# NMS (Notice Monitoring System)

정부/기관 공지사항 페이지를 하루 두 번(KST 09:00, 18:00) 자동으로 확인해서
새 글이나 기존 글의 변경을 이메일로 알려주는 시스템.

전체 설계 배경과 구조는 [ARCHITECTURE.md](./ARCHITECTURE.md) 참고.

## 1. 로컬에서 테스트하기

```bash
pip install -r requirements.txt

# .env.example을 참고해 환경변수 설정 (Gmail이면 "앱 비밀번호" 필요)
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=465
export SMTP_USER=your_account@gmail.com
export SMTP_PASS=your_app_password
export NOTIFY_TO=you@example.com

cd src
python main.py
```

`config/sites.yaml`의 `sites:` 목록이 비어 있으면 "설정된 사이트가 없습니다"만 출력하고
종료한다. 아래 2번을 따라 사이트를 하나 이상 추가해야 실제로 동작한다.

## 2. 모니터링할 사이트 추가하기

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

### JS로 렌더링되는 사이트(SPA)라서 selectors로 안 잡히는 경우

`src/sites/_template.py`를 복사해서 커스텀 파서를 작성한다. 대부분은 화면이 JS로 그려져도
내부적으로는 JSON을 반환하는 API를 호출하고 있으므로, 브라우저 개발자도구의 Network 탭에서
그 API 요청을 찾아 직접 호출하는 방식이 Playwright 같은 무거운 도구보다 훨씬 간단하다.
이런 사이트는 무료 AI에게 "이 API 응답 예시(JSON)를 보고 파서를 작성해줘"라고 요청하기 좋다.

## 3. GitHub에 배포하기 (아직 안 했다면)

1. GitHub에 **Public** 저장소를 만들고 이 폴더를 push
2. 저장소 Settings → Secrets and variables → Actions에서 아래 Secret 등록
   - `SMTP_HOST` (예: smtp.gmail.com)
   - `SMTP_PORT` (예: 465)
   - `SMTP_USER`
   - `SMTP_PASS` (Gmail이면 앱 비밀번호)
   - `NOTIFY_TO` (여러 명이면 콤마로 구분)
3. `.github/workflows/check_notices.yml`이 매일 KST 09:00/18:00에 자동 실행됨.
   Actions 탭에서 "Run workflow" 버튼으로 수동 실행도 가능.

## 4. 폴더 구조

```
config/sites.yaml     모니터링 대상 사이트 목록 (여기만 수정하면 사이트 추가 가능)
src/main.py           진입점
src/crawler.py        목록 페이지 요청 + 파싱
src/differ.py         신규/변경 판별
src/notifier.py       이메일 발송
src/state_store.py    상태 파일(data/seen_state.json) 읽기/쓰기
src/sites/_template.py  특이 사이트용 커스텀 파서 템플릿
.github/workflows/check_notices.yml  스케줄러
```
