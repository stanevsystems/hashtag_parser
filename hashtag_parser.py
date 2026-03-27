import asyncio
import json
import os
from dotenv import load_dotenv

from telethon import TelegramClient, events

# === Загрузка переменных из .env ===
load_dotenv()  # автоматически ищет файл .env в текущей папке

# Получаем api_id и api_hash
try:
    api_id = int(os.getenv("api_id"))
    api_hash = os.getenv("api_hash")
except (TypeError, ValueError):
    print("❌ Ошибка: api_id или api_hash не найдены в .env файле или имеют неверный формат.")
    print("Проверьте файл .env и убедитесь, что api_id — это число.")
    exit(1)

if not api_id or not api_hash:
    print("❌ Ошибка: api_id и api_hash должны быть указаны в файле .env")
    exit(1)

client = TelegramClient('hashtag_collector_session', api_id, api_hash)

@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    """Обработчик команды /collect #хэштег"""
    raw_tag = event.pattern_match.group(1).strip()
    hashtag = raw_tag if raw_tag.startswith('#') else f'#{raw_tag}'

    await event.reply(f'🔍 Ищу все сообщения с хэштегом **{hashtag}** в этом чате...\n'
                      f'Это может занять время.')

    messages = []
    try:
        async for message in client.iter_messages(
            event.chat_id,
            search=hashtag,
            limit=None  # собираем всю историю
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
        await event.reply(f'❌ Ошибка при поиске: {str(e)}')
        return

    if not messages:
        await event.reply(f'😔 Сообщений с хэштегом **{hashtag}** не найдено.')
        return

    # Сохраняем результат
    filename = f"messages_{hashtag.replace('#', '')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

    await event.reply(
        f'✅ Найдено **{len(messages)}** сообщений с хэштегом **{hashtag}**.\n'
        f'Файл прикреплён ниже.'
    )

    await client.send_file(
        event.chat_id,
        filename,
        caption=f'📁 Все сообщения с {hashtag} из истории чата'
    )


async def main():
    await client.start()
    print('✅ Бот успешно запущен!')
    print('   Команда для использования:')
    print('   /collect #хэштег')
    print('   или')
    print('   /collect хэштег  (без #)')
    await client.run_until_disconnected()


if __name__ == '__main__':
    # Установка библиотеки (можно выполнить один раз):
    # pip install telethon python-dotenv

    asyncio.run(main())