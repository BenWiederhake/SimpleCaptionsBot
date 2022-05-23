#!/usr/bin/env python3

import io
import logging
import os
from PIL import Image, ImageDraw, ImageFont
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

MARGIN = 10
STROKE_WIDTH = 5

BASIC_FONT_100 = ImageFont.truetype(font='impact.ttf', size=100)
# SHA256 should be 00f1fc230ac99f9b97ba1a7c214eb5b909a78660cb3826fca7d64c3af5a14848


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


def rgb_add(rgb1, rgb2):
    return tuple(c1 + c2 for c1, c2 in zip(rgb1, rgb2))


def compute_avg_rgb(img, y):
    akku = (0, 0, 0)
    for x in range(img.width):
        akku = rgb_add(akku, img.getpixel((x, y)))
    return tuple(round(c / img.width) for c in rgb)


def try_render(multiline_text, final_width):
    full_size = BASIC_FONT_100.getsize_multiline(multiline_text, stroke_width=STROKE_WIDTH)
    if full_size[0] > WIDTH_MAX or 2 * full_size[1] > HEIGHT_MAX:
        return None, f'The text would take up {full_size[0]}×{full_size[1]} pixels in the intermediary buffer, but I will only allocate {WIDTH_MAX}×{HEIGHT_MAX // 2} pixels for you. Try inserting more linebreaks or shortening the text, as appropriate.'

    if full_size[0] <= final_width - 2 * MARGIN:
        # We don't want to make the text even bigger than 100 points, so pretend that it'll take up the full width and don't scale it up later.
        full_size = (final_width - 2 * MARGIN, full_size[1])

    raw_img = Image.new('RGBA', full_size, color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(raw_img)
    draw.multiline_text((full_size[0] // 2, 0), multiline_text, font=BASIC_FONT_100, fill=(255, 255, 255, 255), stroke_width=STROKE_WIDTH, stroke_fill=(0, 0, 0, 255), anchor='ma')
    del draw

    assert full_size[0] >= final_width - 2 * MARGIN
    if full_size[0] == final_width - 2 * MARGIN:
        result_img = raw_img
    else:
        new_size = (final_width - 2 * MARGIN, round(full_size[1] * (final_width - 2 * MARGIN)/full_size[0]))
        logger.info(f'Scaling {full_size} down to {new_size}.')
        result_img = raw_img.resize(new_size)

    return result_img, None


def try_compose(text_img, onto_img, y_offset):
    logger.info(f'Composing text {text_img.size}@{text_img.mode} on top of {onto_img.size}@{onto_img.mode}.')
    onto_img.alpha_composite(text_img, (MARGIN, y_offset))


def make_img_out(img_in, caption_request):
    new_height = caption_request.top_padding + img_in.height + caption_request.bottom_padding
    if new_height > HEIGHT_MAX:
        return None, f'Sorry, but the resulting meme would be too large ({new_height} pixels; the maximum is {HEIGHT_MAX}).'

    if len(caption_request.top_text) > 1000 or len(caption_request.bottom_text) > 1000:
        return None, f'Sorry, but that is too much text. try to use at most 1000 characters in the top and bottom, respectively.'

    img_out = Image.new('RGBA', (img_in.width, new_height), (0, 0, 0, 255))

    # Begin with the basic meme image:
    img_out.paste(img_in, (0, caption_request.top_padding))

    # Fill in the background:
    if caption_request.top_padding != 0:
        avg_rgb = compute_avg_rgb(img_in, 0)
        draw = ImageDraw.Draw(img_out)
        draw.rectangle([0, 0, img_out.width - 1, caption_request.top_padding - 1], avg_rgb)
    if caption_request.bottom_padding != 0:
        avg_rgb = compute_avg_rgb(img_in, img_in.height - 1)
        draw = ImageDraw.Draw(img_out)
        draw.rectangle([0, caption_request.top_padding + img_in.height, img_out.width - 1, img_out.height - 1], avg_rgb)

    # Render the text:
    if caption_request.top_text:
        text_img, err_msg = try_render(caption_request.top_text, img_out.width)
        if err_msg is not None:
            return None, f'There is a problem with the top text: {err_msg}'
        try_compose(text_img, img_out, MARGIN)
    if caption_request.bottom_text:
        text_img, err_msg = try_render(caption_request.bottom_text, img_out.width)
        if err_msg is not None:
            return None, f'There is a problem with the bottom text: {err_msg}'
        try_compose(text_img, img_out, img_out.height - text_img.height - MARGIN)

    return img_out.convert('RGB'), None


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

    img_out, error_msg = make_img_out(Image.open(io.BytesIO(photo_data)).convert('RGB'), caption_request)
    if error_msg is not None:
        update.message.reply_text(error_msg)
        return
    assert img_out is not None

    filename = f'generated/{time.time_ns()}_{update.effective_user.id}_{secrets.token_hex(8)}.png'
    logger.info(f'Writing meme by @{update.effective_user.username or "???"} to {filename}')
    img_out.save(filename)

    with open(filename, 'rb') as fp:
        msg_out = update.message.reply_photo(fp)

    BOT.send_photo(secret.OWNER_ID, msg_out.photo[-1], caption=f'From @{update.effective_user.username or "???"}, saved at {filename}.')
    logger.info('Complete success!')


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
