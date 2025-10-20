# -*- coding: utf-8 -*-
import imaplib
import email
from email.header import decode_header
import asyncio
import re
from telegram import Bot

# === НАСТРОЙКИ ===

BOT_TOKEN = "ВАШ-ТОКЕН"
TELEGRAM_USER_ID = 123456789
EMAIL_ADDRESS = "example@gmail.com"
EMAIL_PASSWORD = "ВАШ-ВНЕШНИЙ ПАРОЛЬ"
IMAP_SERVER = "imap.gmail.com"

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def decode_mime_words(s):
    """Декодирует заголовки (например, тему письма)"""
    if not s:
        return ""
    decoded = decode_header(s)
    fragments = []
    for text, charset in decoded:
        if isinstance(text, bytes):
            try:
                fragments.append(text.decode(charset or "utf-8"))
            except Exception:
                fragments.append(text.decode("utf-8", errors="ignore"))
        else:
            fragments.append(text)
    return "".join(fragments)


def html_to_text(html):
    """Удаляет HTML-теги и возвращает читаемый текст"""
    clean = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.DOTALL)
    clean = re.sub(r"<[^>]+>", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


# === ПРОВЕРКА ПОЧТЫ ===

async def check_email(bot, last_uid):
    """Проверяет почту и отправляет новые письма"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")

    result, data = mail.uid("search", None, "ALL")
    uids = data[0].split()

    if uids and uids[-1] != last_uid:
        result, data = mail.uid("fetch", uids[-1], "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_words(msg["Subject"])
        sender = decode_mime_words(msg["From"])

        body = ""
        text_found = False  # чтобы знать, был ли найден текст

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Сначала ищем text/plain
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body_bytes = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = body_bytes.decode(charset, errors="ignore")
                        text_found = True
                        break
                    except Exception:
                        pass

                # Если нет text/plain — используем text/html
                elif not text_found and content_type == "text/html":
                    try:
                        body_bytes = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        html_content = body_bytes.decode(charset, errors="ignore")
                        body = html_to_text(html_content)
                    except Exception:
                        pass
        else:
            body_bytes = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            raw_body = body_bytes.decode(charset, errors="ignore")
            if msg.get_content_type() == "text/html":
                body = html_to_text(raw_body)
            else:
                body = raw_body

        if len(body) > 3500:
            body = body[:3500] + "\n\n(сообщение обрезано)"

        text = f"📧 Новое письмо!\nОт: {sender}\nТема: {subject}\n\n{body}"
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=text)
        return uids[-1]

    return last_uid


def get_last_uid_on_start():
    """Возвращает UID последнего письма при запуске"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")
    result, data = mail.uid("search", None, "ALL")
    uids = data[0].split()
    if uids:
        return uids[-1]
    return None


# === ОСНОВНОЙ ЦИКЛ ===

async def main():
    bot = Bot(token=BOT_TOKEN)
    last_uid = get_last_uid_on_start()
    while True:
        try:
            last_uid = await check_email(bot, last_uid)
        except Exception as e:
            print("Ошибка:", e)
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())

