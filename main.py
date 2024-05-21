import requests
import nest_asyncio
import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import schedule
import time
from telegram.constants import ParseMode
import threading

TELEGRAM_TOKEN = '6863087388:AAGjhycCH4mBeSlYnApQrvi1hovbKTL9P7Q'
STEAM_API_KEY = '27333E51E5E05A41BDCA5EA437F99DE7'
STEAM_IDS = {
    'Миша': '76561198892381372',
    'Костя': '76561198958255573',
    'Дима': '76561198180012983',
    'Владик': '76561199171178139'
}
CHAT_ID = '-1001756350079'

nest_asyncio.apply()

bot = Bot(token=TELEGRAM_TOKEN)

player_status = {name: {'is_playing': False, 'session_start_time': None, 'game_info': None, 'game_icon_url': None} for name in STEAM_IDS}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Проверить статус игроков", callback_data="check_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажмите кнопку, чтобы проверить статус игроков:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == "check_status":
        playing_users = []
        for player_name, status in player_status.items():
            if status['is_playing']:
                session_duration = time.time() - status['session_start_time']
                session_duration_str = time.strftime("%H:%M:%S", time.gmtime(session_duration))
                game_info = status['game_info']
                game_icon_url = status['game_icon_url']
                playing_users.append(f"{player_name} играет в {game_info} (Сессия: {session_duration_str})")
                if game_icon_url:
                    await bot.send_photo(chat_id=CHAT_ID, photo=game_icon_url, caption=f"{player_name} играет в {game_info} (Сессия: {session_duration_str})")
        message = "Сейчас играют:\n" + "\n".join(playing_users) if playing_users else "Сейчас никто не играет."
        await query.edit_message_text(text=message)

def send_message(chat_id, message):
    asyncio.run(bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML))

def get_game_icon_url(game_name):
    search_url = f"https://store.steampowered.com/api/storesearch?term={game_name}&cc=us&l=en"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        search_data = response.json()
        if search_data['total'] > 0:
            appid = search_data['items'][0]['id']
            game_icon_url = f"https://cdn.akamai.steamstatic.com//steam//apps//{appid}//capsule_231x87.jpg"
            return game_icon_url
    except requests.exceptions.RequestException as e:
        print(f"Failed to get game icon URL: {e}")
    return None

def check_player_status(player_name, steam_id):
    global player_status
    player_summaries_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam_id}"
    try:
        summaries_response = requests.get(player_summaries_url)
        summaries_response.raise_for_status()
        summaries_data = summaries_response.json()
        for player in summaries_data['response']['players']:
            if 'gameextrainfo' in player:
                game_info = player['gameextrainfo']
                if not player_status[player_name]['is_playing']:
                    player_status[player_name]['is_playing'] = True
                    player_status[player_name]['session_start_time'] = time.time()
                    player_status[player_name]['game_info'] = game_info
                    game_icon_url = get_game_icon_url(game_info)
                    player_status[player_name]['game_icon_url'] = game_icon_url
                    message = f"🚨😲🎮 {player['personaname']} играет в {game_info}"
                    send_message(CHAT_ID, message)
            else:
                if player_status[player_name]['is_playing']:
                    player_status[player_name]['is_playing'] = False
                    player_status[player_name]['game_info'] = None
                    player_status[player_name]['game_icon_url'] = None
                    session_end_time = time.time()
                    session_duration = session_end_time - player_status[player_name]['session_start_time']
                    session_duration_str = time.strftime("%H:%M:%S", time.gmtime(session_duration))
                    message = f"❌ {player['personaname']} вышел из игры. Время сессии: {session_duration_str}"
                    send_message(CHAT_ID, message)
    except Exception as e:
        print(f"Error checking player status: {e}")

def check_all_players():
    for player_name, steam_id in STEAM_IDS.items():
        check_player_status(player_name, steam_id)

def job():
    check_all_players()

schedule.every(1).seconds.do(job)

application = Application.builder().token(TELEGRAM_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    threading.Thread(target=run_schedule).start()
    application.run_polling()
