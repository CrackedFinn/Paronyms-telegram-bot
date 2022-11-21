Dict = open("Dict.txt", encoding="utf8").readlines()
Emoji = open("Emoji Set.txt", encoding="utf8").readlines()
Greet = open("Greeting Set.txt", encoding="utf8").readlines()
import random
import emoji
from aiogram import Bot, Dispatcher, executor, types
from aiogram_broadcaster import TextBroadcaster
import asyncio
import aioschedule
import mysql.connector
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

dbc = urlparse(str(os.getenv('MYSQL_URL')))  # Parse and connect MySQl url
mydb = mysql.connector.connect(
    host=dbc.netloc.split(":")[1].split("@")[1],
    user=dbc.netloc.split(":")[0],
    passwd=dbc.netloc.split(":")[1].split("@")[0],
    database=dbc.path[1:],
    port=dbc.netloc.split(":")[2]
)

NUM = ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
# IMPORT#

# INIT#
defCount = 0  # ReCount an amount of words in dictionary at start
for i in range(len(Dict)):
    if len(Dict[i]) == 1:
        defCount += 1


# MAIN#
def post():  # Returns formatted HTML message
    ShiftCounter = 0
    randomShift = random.randint(0, defCount - 1)
    for i in range(len(Dict)):
        if len(Dict[i]) == 1:
            if randomShift == ShiftCounter:
                header = Dict[i + 1]
                GenStr = ''
                for y in range(header.count(" – ") + 1):
                    base = Dict[i + y + 2][:-1]
                    if base.count(NUM[0]) == 0:
                        definition = base.split(' ', 1)
                        GenStr += ('\n\n' + "<b>" + definition[0] + "</b> <i>" + definition[1] + "</i>")
                    else:
                        definition = base.split(' – ', 1)
                        Lines = definition[1]
                        for w in range(len(NUM)):
                            Lines = Lines.replace(NUM[w], str('\n' + NUM[w]))
                        GenStr += '\n\n' + "<b>" + definition[0] + ":" + "</b><i>" + Lines + "</i>"
                if header.count('–') == 1:
                    headerFix = header.replace('–', 'или')[:-1]
                else:
                    headerFix = header.replace(' – ', ', ', header.count('–') - 1).replace('–', 'или')[:-1]
                message = (emoji.emojize(Emoji[random.randint(0, len(Emoji) - 1)][:-1]) + " "
                           + "<b>" + headerFix + "</b>" + "? "
                           + Greet[random.randint(0, len(Greet) - 1)][:-1] + ':' + GenStr)
                return message
            ShiftCounter += 1


bot = Bot(token=os.getenv('TOKEN'))  # Connect Telegram bot
dp = Dispatcher(bot)


@dp.message_handler(commands=['start']) # Run on /start command
async def send_welcome(message: types.Message):
    # ADD NEW USER TO DB #
    mycursor = mydb.cursor()
    sql = "SELECT * FROM ParonymsUsers WHERE TelegramUserID = %s"
    val = (message.chat.id,)
    mycursor.execute(sql, val)
    myresult = mycursor.fetchall()
    if len(myresult) == 0:
        sql = "INSERT INTO ParonymsUsers (TelegramUserID) VALUE (%s)"
        val = (message.chat.id,)
        mycursor.execute(sql, val)
        mydb.commit()
    # ADD NEW USER TO DB #

    kb = [[types.KeyboardButton(text="Выучить новые слова"), types.KeyboardButton(text="ТехПоддержка")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="")

    await bot.send_message(message.from_user.id, f"Привет, <b>{message.from_user.full_name}!</b>" +
                           '\n\nЯ - бот для изучения паронимов, которые пригодятся тебе для 5-го задания на ЕГЭ.\n\nКаждый день я буду присылать тебе несколько паронимов - так ты сможешь их постепенно выучить.' +
                           "\nА вот и твой первый набор слов: ", parse_mode="HTML")
    await bot.send_message(message.chat.id, post(), parse_mode="HTML", reply_markup=keyboard)
    await bot.send_message(message.chat.id,
                           'Если захочешь потренироваться ещё - просто нажми кнопку <b>"Выучить новые слова"</b> в любое время.',
                           parse_mode="HTML")


async def main():
    mycursor = mydb.cursor()
    mycursor.execute("SELECT TelegramUserID FROM ParonymsUsers")
    myresult = mycursor.fetchall()
    users = [x[0] for x in myresult]

    broadcaster = TextBroadcaster(users, post(), parse_mode="HTML", bot_token=os.getenv('TOKEN'))
    try:
        await broadcaster.run()
    finally:
        await broadcaster.close_bot()


@dp.message_handler(text="Выучить новые слова")
async def with_puree(message: types.Message):
    await bot.send_message(message.chat.id, post(), parse_mode="HTML")


@dp.message_handler(text="ТехПоддержка")
async def without_puree(message: types.Message):
    await bot.send_message(message.chat.id, "Вы можете связаться с техподдержкой здесь: @EmojiCreatorSupportBot",
                           parse_mode="HTML")


async def scheduler():
    aioschedule.every().day.at("7:00").do(main)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
