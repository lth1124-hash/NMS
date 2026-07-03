"""신규/변경/삭제 게시물을 모아 알림을 보낸다.

지원하는 알림 수단(설정된 환경변수에 따라 자동으로 켜짐, 여러 개 동시 사용 가능):
  - ntfy.sh (NTFY_TOPIC 환경변수) - 가입 없이 무료로 쓸 수 있는 푸시 알림. 기본 추천.
  - 이메일 SMTP (SMTP_HOST 환경변수) - Gmail 등 SMTP 계정이 있을 때.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests


def _item_line_html(label: str, item: dict) -> str:
    date_part = f" ({item['date']})" if item.get("date") else ""
    return f'<li>[{label}] <a href="{item["link"]}">{item["title"]}</a>{date_part}</li>'


def _build_html(results: list[dict], failures: list[dict]) -> str:
    parts = ["<html><body>"]

    for r in results:
        if not r["new_items"] and not r["updated_items"] and not r["deleted_items"]:
            continue
        parts.append(f"<h3>{r['site_name']}</h3><ul>")
        for item in r["new_items"]:
            parts.append(_item_line_html("신규", item))
        for item in r["updated_items"]:
            parts.append(_item_line_html("변경", item))
        for item in r["deleted_items"]:
            parts.append(f'<li>[삭제] {item["title"]}{f" ({item["date"]})" if item.get("date") else ""}</li>')
        parts.append("</ul>")

    if failures:
        parts.append("<h3>확인 실패</h3><ul>")
        for f in failures:
            parts.append(f"<li>{f['site_name']}: {f['error']}</li>")
        parts.append("</ul>")

    parts.append("</body></html>")
    return "".join(parts)


def _build_text(results: list[dict], failures: list[dict]) -> str:
    lines = []

    for r in results:
        if not r["new_items"] and not r["updated_items"] and not r["deleted_items"]:
            continue
        lines.append(f"■ {r['site_name']}")
        for item in r["new_items"]:
            lines.append(f"[신규] {item['title']} ({item['date']})\n{item['link']}")
        for item in r["updated_items"]:
            lines.append(f"[변경] {item['title']} ({item['date']})\n{item['link']}")
        for item in r["deleted_items"]:
            lines.append(f"[삭제] {item['title']}")
        lines.append("")

    if failures:
        lines.append("■ 확인 실패")
        for f in failures:
            lines.append(f"{f['site_name']}: {f['error']}")

    return "\n".join(lines).strip()


def _summary(results: list[dict], failures: list[dict]) -> tuple[str, int, int, int]:
    total_new = sum(len(r["new_items"]) for r in results)
    total_updated = sum(len(r["updated_items"]) for r in results)
    total_deleted = sum(len(r["deleted_items"]) for r in results)
    title = f"NMS 신규 {total_new} / 변경 {total_updated} / 삭제 {total_deleted}"
    if failures:
        title += f" / 확인실패 {len(failures)}"
    return title, total_new, total_updated, total_deleted


def has_notifiable_content(results: list[dict], failures: list[dict]) -> bool:
    return (
        any(r["new_items"] or r["updated_items"] or r["deleted_items"] for r in results)
        or bool(failures)
    )


def send_ntfy(results: list[dict], failures: list[dict]) -> None:
    topic = os.environ["NTFY_TOPIC"]
    title, *_ = _summary(results, failures)
    body = _build_text(results, failures)

    # JSON body로 보내면 한글 제목/본문이 HTTP 헤더 인코딩 문제 없이 그대로 전달된다.
    resp = requests.post(
        "https://ntfy.sh/",
        json={"topic": topic, "title": title, "message": body},
        timeout=15,
    )
    resp.raise_for_status()


def send_email(results: list[dict], failures: list[dict]) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    to_addrs = [a.strip() for a in os.environ["NOTIFY_TO"].split(",") if a.strip()]

    subject, *_ = _summary(results, failures)
    subject = f"[NMS] {subject}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(_build_html(results, failures), "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addrs, msg.as_string())


def send_all(results: list[dict], failures: list[dict]) -> None:
    """환경변수로 설정된 알림 수단에 전부 보낸다. 하나도 설정 안 돼있으면 콘솔에만 찍는다."""
    sent = False

    if os.environ.get("NTFY_TOPIC"):
        send_ntfy(results, failures)
        print("ntfy 알림 발송 완료")
        sent = True

    if os.environ.get("SMTP_HOST"):
        send_email(results, failures)
        print("이메일 발송 완료")
        sent = True

    if not sent:
        print("알림 수단이 설정되지 않았습니다 (NTFY_TOPIC 또는 SMTP_HOST). 아래 내용만 출력합니다.")
        print(_build_text(results, failures))
