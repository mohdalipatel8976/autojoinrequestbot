import asyncio
import os
import sys
from datetime import datetime, timedelta
from time import time, sleep
import logging

from pyrogram import Client, idle
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, ChatMemberUpdatedHandler, ChatJoinRequestHandler
from pyrogram.session.session import Session
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import Database



logging.basicConfig(
    level=logging.DEBUG,  # Set to logging.INFO in production
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot_debug.log"),  # Save logs to a file
        logging.StreamHandler(sys.stdout)  # Print logs to console
    ]
)

async def pyro(token):
    """ Initializes the Telegram bot session """
    logging.info("Initializing bot session...")
    try:
        API_HASH = '8d19c8dba1c991434ae421ec66f3d1c4'  # Add your API Hash
        API_ID = '23516855'    # Add your API ID

        bot_id = str(token).split(':')[0]
        app = Client(
            'sessioni/session_bot' + str(bot_id),
            api_hash=API_HASH,
            api_id=API_ID,
            bot_token=token,
            workers=20,
            sleep_threshold=30
        )
        logging.info(f"Bot {bot_id} initialized successfully.")
        return app
    except Exception as e:
        logging.error(f"Failed to initialize bot: {e}", exc_info=True)

async def gen_menu(menu):
    menu = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=y['text'], callback_data=y['callback_data']) for y in x] for x in
                         menu])
    return menu

async def edit(client, chat_id, text=False, menu=False, msg_id=False, cb_id=False, not_text=False):
    if msg_id:
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=menu
            )
        except:
            pass

    if cb_id:
        try:
            await client.answer_callback_query(
                callback_query_id=cb_id,
                text=not_text
            )
        except:
            pass




async def wrap_send_del(bot: Client, chatid: int, text: str, menu: InlineKeyboardMarkup):
    delete = await db.getLastmsg(chatid)
    delete = delete[0]
    if int(delete) != 0:
        try:
            await bot.delete_messages(chatid, int(delete))
        except:
            pass
    try:
        send = await bot.send_message(chatid, text, reply_markup=menu)
        await db.updateLastmsg(send.id, chatid)
    except Exception as e:
        print("EXC in wrap_send_del:", e)

async def mandaPost(bot, chat_to, chat_from, msg_id):
    try:
        await bot.copy_message(chat_id=chat_to, from_chat_id=chat_from, message_id=msg_id)
    except Exception as e:
        print(str(e))

async def accettareq(bot, update, tempo):
    await asyncio.sleep(tempo)
    try:
        await bot.approve_chat_join_request(update.chat.id, update.from_user.id)
    except:
        pass
    return




#           -= HANDLERS =-         #
async def update_handler_cb(bot, message):
    await bot_handler(bot, message, True)

async def requests_handler(bot, update):
    canali = await db.getCanale(update.chat.id)
    if not canali: return

    t1 = time()
    print("ricevuta request")

    tempo = await db.getTempo(update.chat.id)
    now = datetime.now()
    try:
        # Skip if out of range (7 days)
        if int(temp[0]) < LIMIT:
            orario = now + timedelta(minutes=tempo[0])
            futuroMenoOra = orario - now
            secondiDaSleppare = futuroMenoOra.total_seconds()
            asyncio.create_task(accettareq(bot, update, secondiDaSleppare))
    except:
        print("EXC ON TEMPO", tempo)

    welcome = await db.getWelcome(update.chat.id)
    if welcome[0] != "0":
        welcome = welcome[0].split(":")
        await bot.copy_message(update.from_user.id, int(welcome[1]), int(welcome[0]))
    await db.adduser(update.from_user.id)

    print('Ended in:', round(time() - t1, 4), '\n')
    return

async def channel_handler(bot, update):
    old_member = update.old_chat_member
    new_member = update.new_chat_member
    if old_member and not old_member.user.id == DEFAULT_BOT_ID: return
    if new_member and not new_member.user.id == DEFAULT_BOT_ID: return
    if not update.chat.type == ChatType.CHANNEL: return

    evento = "Update sul bot in un canale avvenuto! "
    t1 = time()
    if (
            not update.old_chat_member or update.old_chat_member.status == ChatMemberStatus.BANNED):  # controllo se l'evento è specificamente di aggiunta
        print(evento + "Evento handlato di tipo: Bot aggiunto")
        conto = await db.getChannelsCount(update.from_user.id)
        if conto[0][0] < 20 or update.from_user.id in ADMINS:
            try:
                await bot.send_message(update.from_user.id, "✅ Admin: <a href='tg://user?id=" + str(
                    update.from_user.id) + "'>" + update.from_user.first_name + "</a>\nadded the bot to channel: " + update.chat.title + " | <code>" + str(
                    update.chat.id) + "</code>")
            except Exception as e:
                print(str(e))
            welcome = await db.getDefaultWelcome(update.from_user.id)
            tempoAttesa = await db.getDefaultTime(update.from_user.id)
            await db.addchannel(update.chat.id, update.from_user.id, welcome[0], tempoAttesa[0])
        else:
            try:
                await bot.send_message(update.from_user.id, "You reached 40/40 channels, can't add more")
            except Exception as e:
                print(str(e))

    elif (
            not update.new_chat_member or update.new_chat_member.status == ChatMemberStatus.BANNED):  # controllo se l'evento è specificamente di rimozione
        print(
            evento + "Evento handlato di tipo: Bot rimosso")  # ovviamente se il bot viene rimosso anche da gente non admin del bot va tolto il canale se no casino
        await db.removechannel(update.chat.id)
        try:
            await bot.send_message(update.from_user.id,
                                   "❌ Bot was removed from channel: " + update.chat.title + " | <code>" + str(
                                       update.chat.id) + "</code>")
        except Exception as e:
            print(str(e))

    else:
        return

    print('Ended in:', round(time() - t1, 4), '\n')
    return

async def bot_handler(bot, message, is_callback=False):
    if is_callback:
        original = message
        cbid = original.id
        msgid = original.message.id
        userid = original.from_user.id
        nome = original.from_user.first_name
        try:
            text = str(original.data)
        except:
            return

        message = message.message

    # Blocca i gruppi
    chatid = message.chat.id
    if chatid < 0:
        return

    # Nome ed ID non in callback
    if not is_callback:
        userid = message.from_user.id
        nome = message.from_user.first_name

        # Escludo i media
        try:
            text = str(message.text)
        except:
            pass

    print('Text: ' + str(text))

    # -== CODICE BOT -== #
    t1 = time()
    # Sezione principale
    if text == '/start':
        await db.adduser(userid)
        menu = [
            [
                {'text': '➕ Add channel', 'callback_data': '/add'},
                {'text': 'Remove channel ➖', 'callback_data': '/remove'},
            ],
            [
                {'text': '🗂 Channel management', 'callback_data': '/main'},
            ]
        ]

        if userid in ADMINS:
            menu.append([{'text': 'Bot admins 📃', 'callback_data': '/admin'}, ])

        menu = await gen_menu(menu)
        text = "👋🏻 <b>Welcome <a href='tg://user?id=" + str(userid) + "'>" + str(
            nome) + "</a></b> in your channel manager bot!\n<i>With this bot you will be able to automatically send a welcome message to new members and approve requests to join your channels</i>"
        text += "\n\n👤 By default there is no welcome message for channels, you can set one by replying to a message with <code>/welcome ChannelID</code>, show welcome message for a channel with <code>/testwelcome ChannelID</code> and remove it with <code>/removewelcome ChannelID</code>\n\n📆You can edit time to approve join request for a channel by typing <code>/time ChannelID X</code> where x is the amount of time in minutes you want the requests to be accepted after."
        welcome = await db.getDefaultWelcome(userid)
        tempoAttesa = await db.getDefaultTime(userid)
        text += f"\n\nDefault time: {tempoAttesa[0]} minutes (to edit: <code>/deftime x</code>)"
        text += f"\nDef welcome: {'✅' if welcome[0] != '0' else '❌'} (edit: <code>/defwelcome</code> reply, show: <code>/testdefwelcome</code>)"
        if is_callback:
            await edit(bot, chatid, text, menu, msgid, cbid)
        else:
            await wrap_send_del(bot, chatid, text, menu)

        await db.adduser(userid)

    elif text == '/admin':
        if not is_callback: return
        text = '👮 <b>ADMIN LIST: </b>\n\n'
        for x in ADMINS:
            text += " • <a href='tg://user?id=" + str(x) + "'>" + str(x) + "</a>\n"
        text += "\nTo add or remove admins that can manage this bot contact <i>@Rvwinproof_bot</i>"
        text += "\n\nTo send promotion post to EVERYONE who has ever interacted with the bot, send <code>/post</code> in reply to a message."
        text += "\nAdmins can add unlimited channels to the bot."
        menu = [
            [
                {'text': '🔙 Back', 'callback_data': '/start'},
            ]
        ]
        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)


    elif text == '/post':
        if userid in ADMINS:
            if message.reply_to_message is not None:
                await bot.send_message(chatid,
                                       "💬 Starting to send promotion to everyone, many minutes may be required, don't touch anything else in the meanwhile..")
                cazzo = await db.getUsers()
                for x in cazzo:
                    await asyncio.sleep(0.5)
                    asyncio.create_task(mandaPost(bot, x[0], chatid, message.reply_to_message.id))
                    text = "👍 Sent post successfully to everyone."
            else:
                text = "👎 Command must be in reply to a message you want to promote."
            menu = [
                [
                    {'text': '🔙 Back', 'callback_data': '/start'},
                ]
            ]
            menu = await gen_menu(menu)
            await wrap_send_del(bot, chatid, text, menu)

    elif text == '/add':
        if not is_callback: return
        text = "ℹ️ <b>How does this work?</b>\nYou'll just need to add this bot (@" + bot.me.username + ") in all the channels you want to manage and they will appaear in the bot!\n(You can add max 20 channels)\n\n⚠️ <b>Notice</b>: If after adding the bot to a channel <u>no notification comes here</u>, you'll need to remove and add it again, if the problem still occurs contact @Rvwinproof_bot."

        menu = [
            [
                {'text': '🔙 Back', 'callback_data': '/start'},
            ]
        ]
        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)

    elif text == '/remove':
        if not is_callback: return
        canali = await db.getChannels(userid)
        menu = []
        if canali:
            for canale in canali:
                info = await bot.get_chat(canale[0])
                menu.append([
                    {'text': "🔻 " + info.title, 'callback_data': '/rimuovi' + str(canale[0])}
                ])
        menu.append([
            {'text': '🔙 Back', 'callback_data': '/start'}
        ])
        menu = await gen_menu(menu)
        text = '✖️ <b>Click the bot you want to remove</b>'
        await edit(bot, chatid, text, menu, msgid, cbid)

    elif text.startswith('/rimuovi'):
        if not is_callback: return
        canale = text.replace('/rimuovi', '')
        check = await db.getChannelCheckAdmin(canale, userid)
        if check is not None:
            try:
                info = await bot.get_chat(canale)
                await bot.leave_chat(canale)
            except:
                pass
            text = "Channel removed successfully 👍"
            menu = [
                [
                    {'text': '🔙 Back', 'callback_data': '/remove'},
                ]
            ]
            menu = await gen_menu(menu)
            await edit(bot, chatid, text, menu, msgid, cbid)

    elif text == '/main':
        if not is_callback: return

        conto = await db.getChannelsCount(userid)
        maxch = f"{'Unlimited' if userid in ADMINS else '20'}"
        text = f"<b>Your Channels</b>: {conto[0][0]}/{maxch}\n"
        menu = [[{'text': '🏘 Home', 'callback_data': '/start'}, ]]

        canali = await db.getChannels(userid)
        if canali:
            '''liste=[canali[i:i + chunk] for i in range(0, len(canali), chunk)]'''
            for x in canali:
                info = await bot.get_chat(x[0])
                tempo = await db.getTempo(x[0])
                welcome = await db.getWelcome(x[0])
                text += f"\n{info.title}: <code>{x[0]}</code>, time: {tempo[0]} minutes, welcome set: {'✅' if welcome[0] != '0' else '❌'}"

        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)


    elif text.startswith('/time'):
        splitText = text.split()
        if len(splitText) != 3:
            text = "👎 Correct mode is: <code>/time ChannelID x</code>"
        else:
            channelID = text.split()[1]
            minutesTime = text.split()[2]
            check = await db.getChannelCheckAdmin(channelID, userid)
            if check is not None:
                await db.updateTempo(minutesTime, channelID)
                text = "👍 Time for channel " + channelID + " updated successfully to " + minutesTime
            else:
                text = "👎 Not your channel"

        menu = [
            [
                {'text': '🔙 Back', 'callback_data': '/main'},
            ]
        ]
        menu = await gen_menu(menu)
        await wrap_send_del(bot, chatid, text, menu)

    elif text.startswith('/deftime'):
        splitText = text.split()
        if len(splitText) != 2:
            text = "👎 Correct mode is: <code>/deftime x</code>"
        else:
            minutesTime = text.split()[1]
            await db.updateDefaultTime(minutesTime, userid)
            text = "👍 Default time updated successfully to " + minutesTime

        menu = [
            [
                {'text': '🔙 Back', 'callback_data': '/main'},
            ]
        ]
        menu = await gen_menu(menu)
        await wrap_send_del(bot, chatid, text, menu)

    elif text == '/defwelcome':
        if message.reply_to_message is not None:
            await db.updateDefaultWelcome(str(message.reply_to_message.id) + ":" + str(chatid), userid)
            text = "👍 Default welcome updated successfully"
        else:
            await db.updateDefaultWelcome("0", userid)
            text = "👍 Default welcome removed successfully"
        menu = [
            [
                {'text': '🔙 Back', 'callback_data': '/main'},
            ]
        ]
        menu = await gen_menu(menu)
        await wrap_send_del(bot, chatid, text, menu)

    elif text.startswith('/testdefwelcome'):
        welcome = await db.getDefaultWelcome(userid)
        if welcome[0] != "0":
            welcome = welcome[0].split(":")
            await bot.copy_message(chatid, int(welcome[1]), int(welcome[0]))
            await bot.send_message(chatid,
                                   f"⬆️⬆️⬆️ This is the default welcome message, if you don't see anything we reccomend setting another welcome message, if you want to remove it send <code>/removedefwelcome</code>")
        else:
            await bot.send_message(chatid, "❌ No default welcome message set")

    elif text.startswith('/welcome'):
        if message.reply_to_message is not None:
            splitText = text.split()
            if len(splitText) != 2:
                text = "👎 Correct mode is in reply: <code>/welcome ChannelID</code>"
            else:
                channelID = text.split()[1]
                check = await db.getChannelCheckAdmin(channelID, userid)
                if check is not None:
                    await db.updateWelcome(str(message.reply_to_message.id) + ":" + str(chatid), channelID)
                    text = "👍 Welcome for " + channelID + " updated successfully"
                else:
                    text = "👎 Not your channel"

            menu = [
                [
                    {'text': '🔙 Back', 'callback_data': '/main'},
                ]
            ]
            menu = await gen_menu(menu)
            await wrap_send_del(bot, chatid, text, menu)

    elif text.startswith('/testwelcome'):
        splitText = text.split()
        if len(splitText) != 2:
            await bot.send_message(chatid, "❌ Use <code>/testwelcome ChannelID</code>")
        else:
            check = await db.getChannelCheckAdmin(splitText[1], userid)
            if check is not None:
                welcome = await db.getWelcome(splitText[1])
                if welcome[0] != "0":
                    welcome = welcome[0].split(":")
                    await bot.copy_message(chatid, int(welcome[1]), int(welcome[0]))
                    await bot.send_message(chatid,
                                           f"⬆️⬆️⬆️ This is the welcome message for channel {splitText[1]}, if you don't see anything we reccomend setting another welcome message")
                else:
                    await bot.send_message(chatid, "❌ No welcome message set")
            else:
                await bot.send_message(chatid, "❌ Not your channel")


    elif text.startswith('/removewelcome'):
        splitText = text.split()
        if len(splitText) != 2:
            await bot.send_message(chatid, "❌ Use <code>/removewelcome ChannelID</code>")
        else:
            check = await db.getChannelCheckAdmin(splitText[1], userid)
            if check is not None:
                await db.updateWelcome("0", splitText[1])
                await bot.send_message(chatid, f"👍 Welcome removed for channel {splitText[1]}")
            else:
                await bot.send_message(chatid, "❌ Not your channel")

    elif text.startswith('/removedefwelcome'):
        await db.updateDefaultWelcome("0", userid)
        await bot.send_message(chatid, f"👍 Default welcome removed")

    elif text.startswith('/goodbye'):
        if message.reply_to_message is not None:
            splitText = text.split()
            if len(splitText) != 2:
                text = "👎 Correct mode is in reply: <code>/goodbye ChannelID</code>"
            else:
                channelID = text.split()[1]
                check = await db.getChannelCheckAdmin(channelID, userid)
                if check is not None:
                    await db.updateGoodbye(str(message.reply_to_message.id) + ":" + str(chatid), channelID)
                    text = "👍 Goodbye for " + channelID + " updated successfully"
                else:
                    text = "👎 Not your channel"

            menu = [
                [
                    {'text': '🔙 Back', 'callback_data': '/main'},
                ]
            ]
            menu = await gen_menu(menu)
            await wrap_send_del(bot, chatid, text, menu)

    elif text.startswith('/testgoodbye'):
        splitText = text.split()
        if len(splitText) != 2:
            await bot.send_message(chatid, "❌ Use <code>/testgoodbye ChannelID</code>")
        else:
            check = await db.getChannelCheckAdmin(splitText[1], userid)
            if check is not None:
                goodbye = await db.getGoodbye(splitText[1])
                if goodbye[0] != "0":
                    goodbye = goodbye[0].split(":")
                    await bot.copy_message(chatid, int(goodbye[1]), int(goodbye[0]))
                    await bot.send_message(chatid,
                                        f"⬆️⬆️⬆️ This is the goodbye message for channel {splitText[1]}, if you don't see anything we recommend setting another goodbye message")
                else:
                    await bot.send_message(chatid, "❌ No goodbye message set")
            else:
                await bot.send_message(chatid, "❌ Not your channel")

    elif text.startswith('/removegoodbye'):
        splitText = text.split()
        if len(splitText) != 2:
            await bot.send_message(chatid, "❌ Use <code>/removegoodbye ChannelID</code>")
        else:
            check = await db.getChannelCheckAdmin(splitText[1], userid)
            if check is not None:
                await db.updateGoodbye("0", splitText[1])
                await bot.send_message(chatid, f"👍 Goodbye removed for channel {splitText[1]}")
            else:
                await bot.send_message(chatid, "❌ Not your channel")


    # INPUT VARI | No comandi
    elif not text.startswith('/'):
        await bot.send_message(chatid, "Press /start to begin")

    print('Ended in:', round(time() - t1, 4), '\n')
    return

async def member_left_handler(bot, update):
    # Check if the update is about a member leaving the channel
    if update.old_chat_member and update.new_chat_member and update.new_chat_member.status == ChatMemberStatus.LEFT:
        chat_id = update.chat.id
        user_id = update.old_chat_member.user.id

        # Get the goodbye message for the channel
        goodbye = await db.getGoodbye(chat_id)
        if goodbye and goodbye[0] != "0":
            goodbye = goodbye[0].split(":")
            await bot.copy_message(user_id, int(goodbye[1]), int(goodbye[0]))


async def main(bot_id=False):
    if not bot_id:
        bot_id = DEFAULT_BOT_ID

    print(f'Genero sessione [{bot_id}] > ', end='')
    SESSION = await pyro(token=TOKEN)
    HANDLERS = {
        'msg': MessageHandler(bot_handler),
        'call': CallbackQueryHandler(update_handler_cb),
        'channel': ChatMemberUpdatedHandler(channel_handler),
        'requests': ChatJoinRequestHandler(requests_handler),
        'member_left': ChatMemberUpdatedHandler(member_left_handler)  # Add the new handler
    }
    SESSION.add_handler(HANDLERS['msg'])
    SESSION.add_handler(HANDLERS['call'])
    SESSION.add_handler(HANDLERS['channel'])
    SESSION.add_handler(HANDLERS['requests'])
    SESSION.add_handler(HANDLERS['member_left'])  # Register the new handler

    print('avvio > ', end='')
    await SESSION.start()

    print('avviati!')
    await idle()

    print('Stopping > ', end='')
    await SESSION.stop()

    await db.close()
    loop.stop()
    print('stopped!\n')
    exit()





if __name__ == '__main__':
    chunk = 20
    LIMIT = 1000

    ADMINS = [5943733965]
    TOKEN = '7791639114:AAFJT_UTS1ejtI7gXE_S27-jn6sswVfE6l4'
    PROJECT_NAME = "ali_welcome"

    DEFAULT_BOT_ID = int(TOKEN.split(':')[0])
    WORKDIR = os.getcwd()

    args = sys.argv
    if len(args) > 1:

        # Avvia il bot
        if args[1] == 'start':
            print('Genero > ', end='')
            os.system(f'cd {WORKDIR} && screen -dmS {PROJECT_NAME}_' + str(DEFAULT_BOT_ID) + ' python3 main.py ')
            print('(1) > ', end='')

            print('fine!')
            exit()

        # Ferma il bot
        elif args[1] == 'stop':
            print('Interrompo > ', end='')
            os.system(f'screen -XS {PROJECT_NAME}_' + str(DEFAULT_BOT_ID) + ' quit')
            print('(1) > ', end='')
            sleep(1)

            print('fine!')
            exit()

        # Prendi ID bot per avviarlo
        else:
            exit('Errore: comando non riconosciuto')

    else:
        bot_id = DEFAULT_BOT_ID

    loop = asyncio.get_event_loop()
    db = Database(loop=loop)
    loop.run_until_complete(main(bot_id))
    exit()
