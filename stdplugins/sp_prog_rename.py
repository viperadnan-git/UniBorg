import asyncio
import re
import html

from telethon import events
from telethon.tl.functions.channels import EditTitleRequest
from telethon.errors.rpcerrorlist import ChatNotModifiedError

MULTI_EDIT_TIMEOUT = 80
REVERT_TIMEOUT = 2 * 60 * 60
DEFAULT_TITLES = {
#    1040270887: 'Programming & Tech',
    1384391544: 'Programming & Tech for girls',
    1286178907: 'test supergroup'
}
rename_lock = asyncio.Lock()
revert_task = None


def fix_title(s):
    # Ideally this would be a state machine, but ¯\_(ツ)_/¯
    def replace(m):
        token = m.group(1)
        if token.lower() == 'and':
            token = '&'
        return token[0].upper() + token[1:] + (' ' if m.group(2) else '')
    return re.sub(r'(\S+)(\s+)?', replace, s)


async def edit_title(chat, title):
    try:
        await borg(EditTitleRequest(
            channel=chat, title=title
        ))
    except ChatNotModifiedError:
        pass  # Everything is ok


async def wait_and_revert(chat_id, timeout):
    await asyncio.sleep(timeout)
    await edit_title(chat_id, DEFAULT_TITLES[chat_id])


@borg.on(events.NewMessage(
    pattern=re.compile(r"(?i)programming (?:&|and) (.+)"),
    chats=list(DEFAULT_TITLES.keys())))
async def on_name(event):
    global revert_task
    new_topic = fix_title(event.pattern_match.group(1))
    new_title = f"Programming & {new_topic}"
    if "Tech" not in new_title:
        new_title += " & Tech"

    if len(new_title) > 255 or rename_lock.locked():
        return

    await event.respond(
        f'<a href="tg://user?id={event.from_id}">{html.escape(event.sender.first_name)}</a>'
        ' changed the group title!',
        parse_mode='html'
    )

    with (await rename_lock):
        await edit_title(event.chat_id, new_title)
        await asyncio.sleep(MULTI_EDIT_TIMEOUT)

    if revert_task and not revert_task.done():
        revert_task.cancel()
    revert_task = asyncio.create_task(
        wait_and_revert(event.chat_id, REVERT_TIMEOUT))
