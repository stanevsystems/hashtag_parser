import asyncio
import json
import os
import sys
from dotenv import load_dotenv

from telethon import TelegramClient, events
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate
from telethon.errors import RPCError

# Загрузка .env
load_dotenv()

# ==================== НАСТРОЙКИ ====================
api_id = int(os.getenv("api_id"))
api_hash = os.getenv("api_hash")

use_proxy = os.getenv("use_proxy", "false").lower() in ("true", "1", "yes", "on")

# Прокси настройки
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
            True,
            os.getenv("proxy_username") or None,
            os.getenv("proxy_password") or None,
        )
        print(f"✅ Прокси включён: {proxy_host}:{proxy_port}")
    else:
        print("⚠️ Прокси включён, но параметры некорректны → будет прямое подключение")
        use_proxy = False
else:
    print("⚡ Прокси отключён (прямое подключение)")

# ==================== КЛИЕНТ ====================
client = TelegramClient(
    'hashtag_collector_session',
    api_id,
    api_hash,
    proxy=proxy,
    connection_retries=25,
    retry_delay=4,
    timeout=45,
    connection=ConnectionTcpMTProxyRandomizedIntermediate if use_proxy else None
)


async def test_connection():
    """Отдельная функция для детального тестирования подключения"""
    print("\n" + "="*60)
    print("🧪 ЗАПУСК ТЕСТА ПОДКЛЮЧЕНИЯ К TELEGRAM")
    print("="*60)

    print(f"API ID:      {api_id}")
    print(f"Use Proxy:   {use_proxy}")
    if use_proxy and proxy:
        print(f"Proxy:       {proxy[1]}:{proxy[2]}")

    try:
        print("\n🔄 Подключаемся к Telegram серверам...")
        await client.connect()

        print("✅ Соединение установлено")

        print("\n🔑 Генерируем/проверяем авторизацию...")
        if not await client.is_user_authorized():
            print("⚠️ Аккаунт не авторизован. Будет выполнен вход...")
            await client.start()
        else:
            print("✅ Аккаунт уже авторизован")

        me = await client.get_me()
        print("\n🎉 Подключение УСПЕШНО!")
        print(f"   Имя:       {me.first_name} {me.last_name or ''}")
        print(f"   Username:  @{me.username}" if me.username else "   Username:  отсутствует")
        print(f"   ID:        {me.id}")

        # Дополнительная диагностика
        print("\n📡 Дополнительная информация:")
        print(f"   DC ID:     {client.session.dc_id}")
        print(f"   Server:    {client.session.server_address}")

        await client.disconnect()
        print("\n✅ Тест завершён успешно. Можно запускать бота.")

    except Exception as e:
        print(f"\n❌ ОШИБКА ПОДКЛЮЧЕНИЯ: {type(e).__name__}")
        print(f"   {e}")
        
        if "timeout" in str(e).lower() or "121" in str(e):
            print("\n💡 Рекомендация: попробуй увеличить таймауты или сменить сервер в v2rayN")
        elif "ConnectionReset" in str(e) or "WinError 64" in str(e):
            print("\n💡 Рекомендация: попробуй другой сервер в прокси-клиенте")
        
        import traceback
        print("\nПолный traceback:")
        traceback.print_exc()


@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    # ... (оставляем как было в предыдущей версии — без изменений)
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
        await event.reply(f'❌ Ошибка: {str(e)}')
        return

    if not messages:
        await event.reply(f'😔 Сообщений с {hashtag} не найдено.')
        return

    filename = f"messages_{hashtag.replace('#', '')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

    await event.reply(f'✅ Найдено **{len(messages)}** сообщений с **{hashtag}**. Файл прикреплён.')
    await client.send_file(event.chat_id, filename, caption=f'Сообщения с {hashtag}')


async def main():
    # Проверка аргументов командной строки
    if len(sys.argv) > 1 and sys.argv[1] in ("--test", "test", "/test"):
        await test_connection()
    else:
        print("🚀 Запуск бота в рабочем режиме...")
        await client.start()
        print("✅ Бот запущен! Напиши в любом чате: /collect #хэштег")
        await client.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())