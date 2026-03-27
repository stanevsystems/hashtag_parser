import asyncio
import json
import os
from dotenv import load_dotenv

from telethon import TelegramClient, events
import socks  # pip install pysocks

# === Загрузка настроек ===
load_dotenv()

api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")

if not api_id or not api_hash:
    print("❌ Ошибка: api_id и api_hash не найдены в .env")
    exit(1)

# === Настройка прокси из .env ===
proxy = None
proxy_type = os.getenv("proxy_type", "").lower()
proxy_host = os.getenv("proxy_host")
proxy_port = os.getenv("proxy_port")

if proxy_type == "socks5" and proxy_host and proxy_port:
    proxy = (
        socks.SOCKS5,
        proxy_host,
        int(proxy_port),
        True,  # rdns
        os.getenv("proxy_username") or None,
        os.getenv("proxy_password") or None,
    )
    print(f"✅ Используется SOCKS5 прокси: {proxy_host}:{proxy_port}")
else:
    print("⚠️ Прокси не настроен — будет прямое подключение (может не работать с VPN)")

# Создаём клиента с прокси
client = TelegramClient(
    'hashtag_collector_session',
    api_id,
    api_hash,
    proxy=proxy,
    connection_retries=15,
    retry_delay=3,
    timeout=30
)

@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    raw_tag = event.pattern_match.group(1).strip()
    hashtag = raw_tag if raw_tag.startswith('#') else f'#{raw_tag}'

    chat_title = event.chat.title if hasattr(event.chat, 'title') and event.chat.title else "Этот чат"
    
    await event.reply(f'🔍 Ищу сообщения с **{hashtag}** в чате:\n**{chat_title}**\n\nЭто может занять время...')

    messages = []
    try:
        async for message in client.iter_messages(event.chat_id, search=hashtag, limit=None):
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
        await event.reply(f'❌ Ошибка поиска: {str(e)}')
        return

    if not messages:
        await event.reply(f'😔 Сообщений с {hashtag} не найдено.')
        return

    filename = f"messages_{hashtag.replace('#', '')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

    await event.reply(
        f'✅ Найдено **{len(messages)}** сообщений с **{hashtag}** в чате **{chat_title}**.\n'
        f'Файл прикреплён.'
    )
    await client.send_file(event.chat_id, filename, caption=f'Все сообщения с {hashtag}')


async def main():
    print("🚀 Запуск клиента...")
    await client.start()
    print("✅ Успешно подключено к Telegram!")
    print("   Теперь добавь этот аккаунт в нужный чат и напиши там:")
    print("   /collect #хэштег")
    await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())