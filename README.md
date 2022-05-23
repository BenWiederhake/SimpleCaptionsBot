# SimpleCaptionsBot

> Captions. More direct than [the memegenerator](https://imgflip.com/memegenerator)

Makes you a caption good.

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [TODOs](#todos)
- [NOTDOs](#notdos)
- [Contribute](#contribute)

## Install

```console
$ # Install Python3 somehow
$ pip3 install --user -r requirements.txt
```

That should be it.

## Usage

- Copy `secret_template.py` to `secret.py`
- Create your bot
    * This means you have to talk to the `@BotFather`: https://web.telegram.org/z/#93372553
    * Do `/newbot`, edit it as much as you like (i.e. description, photo)
    * Copy the API token
- Fill in your own username and ID and the API token in `secret.py`
- Run `bot.py`. I like to run it as `./bot.py 2>&1 | tee bot_$(date +%s).log`, because that works inside screen and I still have arbitrary scrollback.
- You can Ctrl-C the bot at any time and restart it later.
- Maybe clean up the dumps of generated captions in `generated/` from time to time.
- The bot will ping you with new captions. I probably should also implement a way to ban a user.

## TODOs

Improve the Telegram usage, see how it behaves in real life, check whether it interacts nicely with `@gif`.

## NOTDOs

Here are some things this project will definitely (probably) not support:
* Complex interactions
* Complex captions
* Automatic linebreaks?
* Animated captions

## Contribute

Feel free to dive in! [Open an issue](https://github.com/BenWiederhake/SimpleCaptionsBot/issues/new) or submit PRs.
