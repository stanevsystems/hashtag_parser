import asyncio
import json
import os
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

# Загрузка переменных окружения
load_dotenv()

# === Основные настройки ===
api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")

if not api_id or not api_hash:
    print("❌ Ошибка: api_id и api_hash должны быть указаны в .env файле")
    exit(1)

# === Настройки прокси ===
use_proxy = os.getenv("use_proxy", "false").lower() in ("true", "1", "yes", "on")
proxy = None

if use_proxy:
    proxy_type = os.getenv("proxy_type", "socks5").lower()
    proxy_host = os.getenv("proxy_host")
    proxy_port = os.getenv("proxy_port")

    if proxy_type == "socks5" and proxy_host and proxy_port:
        import socks
        proxy = (
            socks.SOCKS5,
            proxy_host,
            int(proxy_port),
            True,                                   # rdns
            os.getenv("proxy_username") or None,
            os.getenv("proxy_password") or None,
        )
        print(f"✅ SOCKS5 прокси включён: {proxy_host}:{proxy_port}")
    else:
        print("⚠️ use_proxy=true, но параметры прокси указаны неверно. Будет прямое подключение.")
        use_proxy = False
else:
    print("⚡ Прокси отключён — используется прямое подключение")

# === Создание клиента с улучшенными параметрами ===
client = TelegramClient(
    'hashtag_collector_session',
    api_id,
    api_hash,
    proxy=proxy,
    connection_retries=20,           # больше попыток
    retry_delay=3,
    timeout=40,
    # Улучшенный транспорт — помогает при проблемах с SOCKS5 и VPN
    connection=ConnectionTcpMTProxyRandomizedIntermediate if use_proxy else None
)

@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    raw_tag = event.pattern_match.group(1).strip()
    hashtag = raw_tag if raw_tag.startswith('#') else f'#{raw_tag}'

    chat_title = getattr(event.chat, 'title', None) or "Этот чат"

    await event.reply(
        f'🔍 Ищу все сообщения с хэштегом **{hashtag}**\n'
        f'в чате: **{chat_title}**\n\n'
        f'⏳ Это может занять время при большой истории...'
    )

    messages = []
    try:
        async for message in client.iter_messages(
            event.chat_id,
            search=hashtag,
            limit=None
        ):
            if message.text:
                messages.append({
                    'date': message.date.isoformat(),
                    'sender_id': message.sender_id,
                    'message_id': message.id,
                    'text': message.text,
                    'link': f"https://t.me/c/{str(event.chat_id)[4:]}/{message.id}"
                    if str(event.chat_id).startswith('-100') else None
                })
    except Exception as e:
        await event.reply(f'❌ Ошибка во время поиска: {str(e)}')
        return

    if not messages:
        await event.reply(f'😔 Сообщений с хэштегом **{hashtag}** в этом чате не найдено.')
        return

    filename = f"messages_{hashtag.replace('#', '')}.json"

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

    await event.reply(
        f'✅ Найдено **{len(messages)}** сообщений с **{hashtag}**.\n'
        f'Файл сохранён и прикреплён.'
    )

    await client.send_file(
        event.chat_id,
        filename,
        caption=f'📁 Все сообщения с {hashtag} из чата "{chat_title}"'
    )


async def main():
    print("🚀 Запуск Telegram Hashtag Collector...")
    try:
        await client.start()
        print("✅ Успешно подключено к Telegram!")
        print("\nКак использовать:")
        print("   1. Добавь этот аккаунт в нужный чат")
        print("   2. Напиши в чате: /collect #хэштег")
        print("      или просто /collect хэштег")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске: {e}")


if __name__ == '__main__':
    asyncio.run(main())