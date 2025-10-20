# -*- coding: utf-8 -*-
import imaplib
import email
from email.header import decode_header
import asyncio
from telegram import Bot

# === НАСТРОЙКИ ===

# Токен бота 
BOT_TOKEN = "ВАШ-ТОКЕН"

# Твой Telegram ID
TELEGRAM_USER_ID = 123456789

# Почта Gmail и пароль приложения (пример для демонстрации)
EMAIL_ADDRESS = "example@gmail.com"
EMAIL_PASSWORD = "ВАШ-ПАРОЛЬ-ДЛЯ-ПРИЛОЖЕНИЙ"

IMAP_SERVER = "imap.gmail.com"

# === ФУНКЦИЯ ДЕКОДИРОВАНИЯ MIME ===
def decode_mime_words(s):
    """Декодирует заголовки письма (например, тему с кириллицей)"""
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

# === ФУНКЦИЯ ПРОВЕРКИ ПОЧТЫ ===
async def check_email(bot, last_uid):
    """Проверяет входящие письма и отправляет новые в Telegram"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")

    # Получаем UID всех писем
    result, data = mail.uid("search", None, "ALL")
    uids = data[0].split()

    # Проверяем, есть ли новое письмо
    if uids and uids[-1] != last_uid:
        result, data = mail.uid("fetch", uids[-1], "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Декодируем тему и отправителя
        subject = decode_mime_words(msg["Subject"])
        sender = decode_mime_words(msg["From"])

        # Извлекаем текст письма
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body_bytes = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = body_bytes.decode(charset, errors="ignore")
                        break
                    except Exception:
                        pass
        else:
            body_bytes = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            body = body_bytes.decode(charset, errors="ignore")

        if len(body) > 3500:
            body = body[:3500] + "\n\n(сообщение обрезано)"

        # Формируем текст уведомления
        text = f"📧 Новое письмо!\nОт: {sender}\nТема: {subject}\n\n{body}"

        # Отправляем сообщение только тебе
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=text)

        return uids[-1]
    else:
        return last_uid

# === ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ПОСЛЕДНЕГО UID ПРИ СТАРТЕ ===
def get_last_uid_on_start():
    """Возвращает UID последнего письма без отправки уведомлений"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")
    result, data = mail.uid("search", None, "ALL")
    uids = data[0].split()
    if uids:
        return uids[-1]
    return None

# === ГЛАВНЫЙ АСИНХРОННЫЙ ЦИКЛ ===
async def main():
    bot = Bot(token=BOT_TOKEN)
    # Получаем последний UID при запуске, чтобы не слать старые письма
    last_uid = get_last_uid_on_start()

    while True:
        try:
            last_uid = await check_email(bot, last_uid)
        except Exception as e:
            print("Ошибка:", e)
        await asyncio.sleep(60)  # проверяем почту каждые 60 секунд

# === ТОЧКА ВХОДА ===
if __name__ == "__main__":
    asyncio.run(main())
