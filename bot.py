#!/usr/bin/env python3

import logging
import os
import secret  # See secret_template.py
import secrets
from telegram import Chat, ChatMember, ChatMemberUpdated, ParseMode, Update
from telegram.ext import (
    CallbackContext,
    ChatMemberHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)
import time

logger = logging.getLogger(__name__)

BOT = None
WIDTH_MIN = 400
WIDTH_MAX = 1800
HEIGHT_MIN = 450
HEIGHT_MAX = 1900


#def cmd_trap(update: Update, _context: CallbackContext) -> None:
#    with open(MEMES.fetch_random_accepted(), 'rb') as fp:
#        update.effective_message.reply_photo(fp, caption="It's a /trap!\n\n(Übrigens, du kannst mir neue Bilder einfach so zuschicken!)")


def cmd_start(update: Update, _context: CallbackContext) -> None:
    update.effective_message.reply_text(
        f'Hi {update.effective_user.first_name}!'
        f'\nSend me a meme along with a caption, and I will put the caption on it.'
        f'\nMake sure to use line breaks if you want a multi-line caption.'
        f'\nLeave an empty line like this to separate top text and bottom text:'
        f'\n'
        f'\nIf the first text line starts with @{secret.BOT_NAME}, or consists only of an underscore, that part is ignored.'
        f'\nIf the first or last line is a number, that many pixels are added to the meme as padding.'
    )


def cmd_photo(update: Update, _context: CallbackContext) -> None:
    update.effective_message.reply_text(
        f'Hi {update.effective_user.first_name}!'
        f'\nYou need to add some text in the message, so I can put it there as a caption.'
        f'\nUse /start@{secret.BOT_NAME} for details.'
    )


class CaptionRequest:
    def __init__(self, top_text, bottom_text, top_padding, bottom_padding):
        self.top_text = top_text
        self.bottom_text = bottom_text
        self.top_padding = top_padding
        self.bottom_padding = bottom_padding

    def __repr__(self):
        return str(self.__dict__)


def clean_part(part):
    return list(filter(lambda x: x, (line.strip() for line in part)))


def try_get_padding(line):
    try:
        padding = int(line, 10)
    except:
        return None
    else:
        return padding


def parse_caption(text):
    # Remove "@TheBot" mention
    if text.startswith(f'@{secret.BOT_NAME}'):
        text = text[len(f'@{secret.BOT_NAME}'):]

    parts = text.split('\n\n', 1)
    assert 1 <= len(parts) <= 2, f'len(parts) == {len(parts)}?! Request was {text}'

    if len(parts) == 1:
        top_part = ''
        bottom_part = parts[0]
    else:
        top_part, bottom_part = parts

    top_part = top_part.splitlines()
    bottom_part = bottom_part.splitlines()

    # Remove superfluous whitespace
    top_part = clean_part(top_part)
    bottom_part = clean_part(bottom_part)

    # Detect padding pixel counts
    top_padding = try_get_padding(top_part[0]) if top_part else None
    if top_padding is None:
        top_padding = 0
    else:
        top_part = top_part[1:]
    bottom_padding = try_get_padding(bottom_part[-1]) if bottom_part else None
    if bottom_padding is None:
        bottom_padding = 0
    else:
        bottom_part = bottom_part[:-1]

    # Remove superfluous whitespace (actually only possible for the bottom part)
    top_part = clean_part(top_part)
    bottom_part = clean_part(bottom_part)

    return CaptionRequest('\n'.join(top_part), '\n'.join(bottom_part), top_padding, bottom_padding)


def cmd_caption(update: Update, _context: CallbackContext) -> None:
    if len(update.message.photo) == 0:
        update.message.reply_text(
            'I really need a meme image, otherwise it will not work.'
        )
        return

    photo = update.message.photo[-1]
    if WIDTH_MIN <= photo.width <= WIDTH_MAX and HEIGHT_MIN <= photo.height <= HEIGHT_MAX:
        pass
    else:
        update.message.reply_text(
            f'Sorry, but it looks like your meme has size {photo.width}×{photo.height},'
            f'but I can only handle memes of size {WIDTH_MIN}×{HEIGHT_MIN} to {WIDTH_MAX}×{HEIGHT_MAX}!'
        )
        return

    photo_file = photo.get_file()
    logger.info(f'Downloading photo from user @{update.effective_user.username} (ID {update.effective_user.id}), about {photo_file.file_size} bytes.')
    photo_data = photo_file.download_as_bytearray()

    caption_request = parse_caption(update.message.caption)

    update.message.reply_text(
        f'Got {len(photo_data)} bytes as meme, got {caption_request} as caption request. Not implemented yet.'
    )
    return

    update.message.reply_text(
        'Awesome! Vielleicht werde ich das bald verwenden. Sorry, es wird kein Feedback darüber geben, das war mir zu kompliziert zu implementieren.'
    )

    filename = f'generated/{time.time_ns()}_{update.effective_user.id}_{secrets.token_hex(8)}.jpg'
    BOT.send_photo(secret.OWNER_ID, photo_file.file_id, caption=f'New meme from @{update.effective_user.username}! Click /accept_{hexname} to accept, or /reject_{hexname} to reject.')


def run():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Alive")

    # Create the Updater and pass it your bot's token.
    updater = Updater(secret.TOKEN)
    global BOT
    BOT = updater.bot

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', cmd_start))

    dispatcher.add_handler(MessageHandler(Filters.caption, cmd_caption))
    dispatcher.add_handler(MessageHandler(Filters.photo, cmd_photo))

    # Start the Bot
    # ALL_TYPES = ['message', 'edited_message', 'channel_post', 'edited_channel_post', 'inline_query', 'chosen_inline_result', 'callback_query', 'shipping_query', 'pre_checkout_query', 'poll', 'poll_answer', 'my_chat_member', 'chat_member', 'chat_join_request']
    # However, we're only interested in actual messages.
    updater.start_polling(allowed_updates=['message'])

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    logger.info("Begin idle loop")
    updater.idle()


if __name__ == '__main__':
    run()
