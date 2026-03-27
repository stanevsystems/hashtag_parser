import asyncio
import json
import os
import sys
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

load_dotenv()

api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")

if not api_id or not api_hash:
    print("❌ Ошибка: api_id и api_hash не найдены в .env")
    sys.exit(1)

# ==================== MTProto ПРОКСИ ====================
use_proxy = os.getenv("use_proxy", "false").lower() in ("true", "1", "yes")
proxy = None
connection = None

if use_proxy:
    proxy_type = os.getenv("proxy_type", "").lower()

    if proxy_type == "mtproto":
        proxy_host = os.getenv("proxy_host")
        proxy_port = int(os.getenv("proxy_port", 443))
        proxy_secret = os.getenv("proxy_secret")

        if proxy_host and proxy_secret:
            proxy = (proxy_host, proxy_port, proxy_secret)
            connection = ConnectionTcpMTProxyRandomizedIntermediate
            print(f"✅ MTProto прокси включён:")
            print(f"   Server : {proxy_host}:{proxy_port}")
            print(f"   Secret : {proxy_secret[:16]}... (скрыто)")
        else:
            print("⚠️ MTProto прокси указан некорректно")
            use_proxy = False
    else:
        print("⚠️ Сейчас поддерживается только MTProto (proxy_type=mtproto)")
        use_proxy = False
else:
    print("⚡ Прокси отключён — прямое подключение")

# ==================== КЛИЕНТ ====================
# client = TelegramClient(
#     'hashtag_collector_session',
#     api_id,
#     api_hash,
#     proxy=proxy,
#     connection=connection,
#     connection_retries=15,
#     retry_delay=3,
#     timeout=40,
# )

# Временный фикс большого api_id
fixed_api_id = api_id if api_id <= 2147483647 else (api_id & 0xFFFFFFFF) - (1 << 32 if api_id & 0x80000000 else 0)

client = TelegramClient(
    'hashtag_collector_session',
    fixed_api_id,          # ← используем исправленное значение
    api_hash,
    proxy=proxy,
    connection=connection,
    connection_retries=15,
    retry_delay=3,
    timeout=40,
)

print(f"Используем api_id: {fixed_api_id} (оригинал был {api_id})")


async def test_connection():
    print("\n" + "="*75)
    print("🧪 ТЕСТ ПОДКЛЮЧЕНИЯ ЧЕРЕЗ MTProto ПРОКСИ")
    print("="*75)
    print(f"Proxy Type : MTProto")
    if proxy:
        print(f"Server     : {proxy[0]}:{proxy[1]}")

    try:
        print("\n🔄 Подключаемся через MTProto прокси...")
        await client.connect()
        print("✅ Соединение установлено")

        print("\n🔑 Проверяем авторизацию...")
        if not await client.is_user_authorized():
            print("⚠️ Выполняем вход в аккаунт...")
            await client.start()
        else:
            print("✅ Аккаунт уже авторизован")

        me = await client.get_me()
        print("\n🎉 УСПЕШНО ПОДКЛЮЧИЛИСЬ!")
        print(f"   Имя     : {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username}" if me.username else "   Username: —")
        print(f"   User ID : {me.id}")

        await client.disconnect()
        print("\n✅ Тест пройден. Теперь можно запускать бота.")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {type(e).__name__}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()


# ==================== Основная команда ====================
@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    raw_tag = event.pattern_match.group(1).strip()
    hashtag = raw_tag if raw_tag.startswith('#') else f'#{raw_tag}'
    chat_title = getattr(event.chat, 'title', None) or "Этот чат"

    await event.reply(f'🔍 Ищу сообщения с **{hashtag}** в чате "**{chat_title}**"...')

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

    await event.reply(f'✅ Найдено **{len(messages)}** сообщений с **{hashtag}**.')
    await client.send_file(event.chat_id, filename, caption=f'Сообщения с {hashtag}')


async def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "test", "/test"):
        await test_connection()
    else:
        print("🚀 Запуск бота с MTProto прокси...")
        await client.start()
        print("✅ Бот запущен! Используй команду /collect #хэштег")
        await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())