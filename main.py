import telebot
from telebot import types
import yt_dlp
import os
import logging

# === Настройки ===
TOKEN = '7775528604:AAENxeb2mGwgnni3mIrg4VgF-7mecVS7bxc'  # заменить на свой токен
bot = telebot.TeleBot(TOKEN)

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Состояния пользователей ===
user_state = {}  # {chat_id: "awaiting_url"}

# === Команда /start ===
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = "awaiting_url"
    bot.send_message(chat_id, "Привет! Пришли ссылку на видео с YouTube. Но обязательно чтобы длитеность ")
    logger.info(f"User {chat_id} started")

# === Обработка URL от пользователя ===
@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "awaiting_url")
def handle_youtube_url(message):
    chat_id = message.chat.id
    url = message.text.strip()
    bot.send_message(chat_id, "Скачиваю видео... Подожди немного.")

    try:
        # Определяем абсолютный путь к папке downloads
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "downloads")
        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            'format': 'best[ext=mp4]',  # Берём уже готовое видео с аудио (если есть)
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'retries': 5,
            'socket_timeout': 60,
        }

        downloaded_file_path = None

        def hook(d):
            nonlocal downloaded_file_path
            if d['status'] == 'finished':
                downloaded_file_path = d['filename']

        ydl_opts['progress_hooks'] = [hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            bot.send_message(chat_id, "Не удалось найти скачанное видео.")
            logger.error(f"File not found after download for user {chat_id}")
            return

        # Используем реальный путь к файлу, полученный через hook
        video_path = downloaded_file_path

        # Логируем полный путь к файлу
        logger.info(f"Video path: {video_path}")

        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if file_size_mb > 49:
            bot.send_message(chat_id, f"Видео слишком большое ({file_size_mb:.2f} МБ).")
            logger.warning(f"Video too large ({file_size_mb:.2f} MB), skipped sending.")
            return

        # Отправляем видео
        with open(video_path, 'rb') as video_file:
            bot.send_video(chat_id, video_file)
        bot.send_message(chat_id, "Видео успешно отправлено!")
        logger.info(f"Sent YouTube video to user {chat_id}")

        # Удаляем файл после отправки
        os.remove(video_path)

    except Exception as e:
        logger.error(f'Error downloading video for user {chat_id}: {e}', exc_info=True)
        bot.send_message(chat_id, f"Ошибка при скачивании или отправке видео: {str(e)}")

    finally:
        if chat_id in user_state:
            del user_state[chat_id]

# === Запуск бота ===
if __name__ == '__main__':
    logger.info("Starting Telegram bot...")
    bot.polling(none_stop=True)