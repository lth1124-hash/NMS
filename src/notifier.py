"""신규/변경/삭제 게시물을 모아 이메일로 발송한다."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _item_line(label: str, item: dict) -> str:
    date_part = f" ({item['date']})" if item.get("date") else ""
    return f'<li>[{label}] <a href="{item["link"]}">{item["title"]}</a>{date_part}</li>'


def _build_html(results: list[dict], failures: list[dict]) -> str:
    parts = ["<html><body>"]

    for r in results:
        if not r["new_items"] and not r["updated_items"] and not r["deleted_items"]:
            continue
        parts.append(f"<h3>{r['site_name']}</h3><ul>")
        for item in r["new_items"]:
            parts.append(_item_line("신규", item))
        for item in r["updated_items"]:
            parts.append(_item_line("변경", item))
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


def has_notifiable_content(results: list[dict], failures: list[dict]) -> bool:
    return (
        any(r["new_items"] or r["updated_items"] or r["deleted_items"] for r in results)
        or bool(failures)
    )


def send_email(results: list[dict], failures: list[dict]) -> None:
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    to_addrs = [a.strip() for a in os.environ["NOTIFY_TO"].split(",") if a.strip()]

    total_new = sum(len(r["new_items"]) for r in results)
    total_updated = sum(len(r["updated_items"]) for r in results)
    total_deleted = sum(len(r["deleted_items"]) for r in results)
    subject = f"[NMS] 신규 {total_new}건 / 변경 {total_updated}건 / 삭제 {total_deleted}건"
    if failures:
        subject += f" / 확인 실패 {len(failures)}건"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(_build_html(results, failures), "html", "utf-8"))

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_addrs, msg.as_string())
