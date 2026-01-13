""" usage: mediawiki-matrix-bot CONFIG

"""
import asyncio
import aiohttp
from typing import Any, Dict, Iterator, Optional
from io import StringIO
from html.parser import HTMLParser
from contextlib import contextmanager
from dataclasses import dataclass
from abc import ABC, abstractmethod

from docopt import docopt
from nio import AsyncClient

import json
import sys

import logging

log = logging.getLogger("bot")
logging.basicConfig(level=logging.INFO)


class MLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d: str) -> None:
        self.text.write(d)

    def get_data(self) -> str:
        return self.text.getvalue()


def strip_tags(html: str) -> str:
    s = MLStripper()
    s.feed(html)
    return s.get_data()


@contextmanager
def die_on_exception(context: str) -> Iterator[None]:
    try:
        yield
    except Exception as e:
        log.error(f"{context}:")
        log.error(e)
        sys.exit(1)


# from the original source: https://github.com/wikimedia/mediawiki/blob/master/includes/rcfeed/IRCColourfulRCFeedFormatter.php
## see http://www.irssi.org/documentation/formats for some colour codes. prefix is \003,
## no colour (\003) switches back to the term default
# $titleString = "\00314[[\00307$title\00314]]";
# $fullString = "$titleString\0034 $flag\00310 " .
# 	"\00302$url\003 \0035*\003 \00303$user\003 \0035*\003 $szdiff \00310$comment\003\n";


# HTML formatting for Matrix
def html_color(text: str, color: str) -> str:
    return f'<font color="{color}">{text}</font>'


def html_bold(text: str) -> str:
    return f"<b>{text}</b>"


# Styled text formatting for Signal (uses markdown-like syntax)
def signal_bold(text: str) -> str:
    return f"**{text}**"


def signal_italic(text: str) -> str:
    return f"*{text}*"


def signal_monospace(text: str) -> str:
    return f"`{text}`"


def format_data_html(obj: Dict[str, Any], baseurl: str, udpinput: bool = False) -> str:
    """Format data as HTML for Matrix. udpinput: set to True if the input arrived via UDP and not via HTTP"""
    log.debug(obj)
    typ = obj["type"]
    if udpinput:
        newrev = obj["revision"]["new"]
        oldrev = obj["revision"]["old"]
        ident = obj["id"]
        old_length = obj.get("length", {}).get("old", None)
        new_length = obj.get("length", {}).get("new", None)
        is_patrolled = obj["patrolled"]
        is_bot = obj["bot"]
        is_minor = obj["minor"]
        log_type = obj.get("log_type", None)
        log_action = obj.get("log_action", None)
        baseurl = f"{obj['server_url']}{obj['server_script_path']}"
        log_action_comment = obj.get("log_action_comment", "")

    else:
        newrev = obj["revid"]
        oldrev = obj["old_revid"]
        ident = obj["rcid"]
        old_length = obj.get("oldlen", None)
        new_length = obj.get("newlen", None)
        is_patrolled = False  # does not work with http (need elevated permissions)
        is_bot = hasattr(obj, "bot")  # do not know if this even works
        is_minor = hasattr(obj, "minor")
        log_type = obj.get("logtype", None)
        log_action = obj.get("logaction", None)
        log_action_comment = obj["comment"]
        baseurl = f"{baseurl}/wiki"

    if typ == "log":
        title = f"Special:Log/{(log_type or 'unknown').capitalize()}"
        url = ""
        flag = log_action or ""
        comment = log_action_comment
    else:
        title = obj["title"]
        comment = obj["comment"]
        flag = ""
        if is_patrolled:
            flag += "!"
        if typ == "new":
            query = f"?oldid={newrev}&rc_id={ident}"
            flag += "N"
        else:
            query = f"?diff={newrev}&oldid={oldrev}"

        if is_minor:
            flag += "M"

        if is_bot:
            flag += "B"

        url = f"{baseurl}/index.php{query}"

    if old_length is not None and new_length is not None:
        diff_length = new_length - old_length
        if diff_length < -500:
            diff_length = html_bold(str(diff_length))  # make large removes bold
        elif diff_length > 0:
            diff_length = f"+{diff_length}"  # add plus sign to additions
        diff_length = f"({diff_length})"
    else:
        diff_length = ""

    user = obj["user"]

    return (
        html_color("[[", "#7F7F7F")
        + html_bold(html_color(title, "#FC7F00"))
        + html_color("]]", "#7F7F7F")
        + " "
        + html_color(flag, "#FF0000")
        + f" {url} {html_color('*','#7F0000')}"
        + f" {html_color(user,'#009300')} {html_color('*','#7F0000')}"
        + f" {html_bold(diff_length)} {html_color(comment,'#009393')}"
    )


def format_data_styled(obj: Dict[str, Any], baseurl: str, udpinput: bool = False) -> str:
    """Format data as styled text for Signal. udpinput: set to True if the input arrived via UDP and not via HTTP"""
    log.debug(obj)
    typ = obj["type"]
    if udpinput:
        newrev = obj["revision"]["new"]
        oldrev = obj["revision"]["old"]
        ident = obj["id"]
        old_length = obj.get("length", {}).get("old", None)
        new_length = obj.get("length", {}).get("new", None)
        is_patrolled = obj["patrolled"]
        is_bot = obj["bot"]
        is_minor = obj["minor"]
        log_type = obj.get("log_type", None)
        log_action = obj.get("log_action", None)
        baseurl = f"{obj['server_url']}{obj['server_script_path']}"
        log_action_comment = obj.get("log_action_comment", "")

    else:
        newrev = obj["revid"]
        oldrev = obj["old_revid"]
        ident = obj["rcid"]
        old_length = obj.get("oldlen", None)
        new_length = obj.get("newlen", None)
        is_patrolled = False  # does not work with http (need elevated permissions)
        is_bot = hasattr(obj, "bot")  # do not know if this even works
        is_minor = hasattr(obj, "minor")
        log_type = obj.get("logtype", None)
        log_action = obj.get("logaction", None)
        log_action_comment = obj["comment"]
        baseurl = f"{baseurl}/wiki"

    if typ == "log":
        title = f"Special:Log/{(log_type or 'unknown').capitalize()}"
        url = ""
        flag = log_action or ""
        comment = log_action_comment
    else:
        title = obj["title"]
        comment = obj["comment"]
        flag = ""
        if is_patrolled:
            flag += "!"
        if typ == "new":
            query = f"?oldid={newrev}&rc_id={ident}"
            flag += "N"
        else:
            query = f"?diff={newrev}&oldid={oldrev}"

        if is_minor:
            flag += "M"

        if is_bot:
            flag += "B"

        url = f"{baseurl}/index.php{query}"

    if old_length is not None and new_length is not None:
        diff_length = new_length - old_length
        if diff_length < -500:
            diff_length = signal_bold(str(diff_length))  # make large removes bold
        elif diff_length > 0:
            diff_length = f"+{diff_length}"  # add plus sign to additions
        diff_length = f"({diff_length})"
    else:
        diff_length = ""

    user = obj["user"]

    # Signal styled format: [[**title**]] *flag* url * user * (diff) *comment*
    return (
        f"[[{signal_bold(title)}]]"
        + f" {signal_italic(flag)}"
        + f" {url} *"
        + f" {signal_bold(user)} *"
        + f" {signal_bold(diff_length)} {signal_italic(comment)}"
    )


class MessageHandler(ABC):
    """Abstract base class for message handlers"""
    
    @abstractmethod
    async def connect(self) -> None:
        """Connect to the messaging service"""
        pass
    
    @abstractmethod
    async def send_message(self, message_obj: Dict[str, Any], baseurl: str) -> None:
        """Send a formatted message"""
        pass
    
    @abstractmethod
    async def run(self) -> None:
        """Run the handler's main loop (if any)"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources"""
        pass


class MatrixHandler(MessageHandler):
    """Handler for sending messages to Matrix"""
    
    def __init__(self, config: Dict[str, Any]):
        self.server = config["server"]
        self.mxid = config["mxid"]
        self.password = config["password"]
        self.room = config["room"]
        self.client: Optional[AsyncClient] = None
    
    async def connect(self) -> None:
        """Connect and login to the Matrix server"""
        log.info(f'login to server {self.server} as {self.mxid}')
        self.client = AsyncClient(self.server, self.mxid)
        log.info(await self.client.login(self.password))
    
    async def send_message(self, message_obj: Dict[str, Any], baseurl: str) -> None:
        if not self.client:
            raise Exception("matrix_client must be connected first")
        html_message = format_data_html(message_obj, baseurl)
        log.info(f"Sending message to {self.room}: {html_message}")
        await self.client.room_send(
            self.room,
            message_type="m.room.message",
            content={
                # fallback for clients not supporting html
                "body": strip_tags(html_message),
                "format": "org.matrix.custom.html",
                "formatted_body": html_message,
                "msgtype": "m.notice",
            },
        )
    
    async def run(self) -> None:
        """Run the Matrix sync loop"""
        if not self.client:
            raise Exception("matrix_client must be connected first")
        with die_on_exception("Something went wrong when syncing with matrix server"):
            await self.client.sync_forever(timeout=30000)
    
    async def close(self) -> None:
        """Close the Matrix client"""
        if self.client:
            await self.client.close()


class SignalHandler(MessageHandler):
    """Handler for sending messages to Signal via REST API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_url = config["signal_api_url"].rstrip("/")
        self.source_number = config["signal_source_number"]
        self.target_group = config["signal_target_group"]
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> None:
        """Create the aiohttp session"""
        log.info(f'Connecting to Signal REST API at {self.api_url}')
        log.info(f'Source number: {self.source_number}, Target group: {self.target_group}')
        self.session = aiohttp.ClientSession()
    
    async def send_message(self, message_obj: Dict[str, Any], baseurl: str) -> None:
        if not self.session:
            raise Exception("Signal session must be connected first")
        
        styled_message = format_data_styled(message_obj, baseurl)
        log.info(f"Sending message to Signal group {self.target_group}: {styled_message}")
        
        payload = {
            "number": self.source_number,
            "recipients": [self.target_group],
            "message": styled_message,
            "text_mode": "styled"
        }
        
        async with self.session.post(
            f"{self.api_url}/v2/send",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            if response.status == 201:
                result = await response.json()
                log.info(f"Message sent successfully: {result}")
            else:
                error_text = await response.text()
                log.error(f"Failed to send Signal message: {response.status} - {error_text}")
                raise Exception(f"Signal API error: {response.status} - {error_text}")
    
    async def run(self) -> None:
        """Signal handler doesn't need a continuous run loop"""
        # Keep running indefinitely - the check_recent_changes task handles polling
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, just to keep the task alive
    
    async def close(self) -> None:
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()


async def fetch_changes(baseurl: str, api_path: str = "/api.php") -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{baseurl}{api_path}?action=query&list=recentchanges&format=json&rcprop=user|comment|flags|title|sizes|loginfo|ids|revision"
        ) as response:
            return await response.json()


async def check_recent_changes(
    handler: MessageHandler,
    config: Dict[str, Any]
) -> None:
    """Check for recent changes and forward them using the provided handler"""
    baseurl = config["baseurl"]
    api_path = config.get("api_path", "/api.php")
    timeout = config.get("timeout", 60)
    
    # initial fetch of the last recent change, there is no state handling here,
    # we do not re-notify changes in case the bot is offline
    log.info("Fetching last changes initially")
    with die_on_exception("Something went wrong when fetching the first change from the wiki"):
        resp = await fetch_changes(baseurl, api_path)
    last_rc = resp["query"]["recentchanges"][0]["rcid"]

    log.info(f"The last rc is {last_rc}")

    while True:
        log.info("check recent changes")
        with die_on_exception("Something went wrong when fetching the latest changes from the wiki"):
            resp = await fetch_changes(baseurl, api_path)
        rcs = resp["query"]["recentchanges"]
        new_rcs = list(filter(lambda x: x["rcid"] > last_rc, rcs))

        if not new_rcs:
            log.info("no new changes")

        for rc in new_rcs:
            with die_on_exception("Something went wrong when forwarding the news"):
                await handler.send_message(rc, baseurl)

        last_rc = rcs[0]["rcid"]  # update last rc
        log.info(f"sleeping for {timeout}")
        await asyncio.sleep(timeout)


def create_handler(config: Dict[str, Any]) -> MessageHandler:
    """Factory function to create the appropriate message handler based on config"""
    handler_type = config.get("type", "matrix")
    
    if handler_type == "matrix":
        return MatrixHandler(config)
    elif handler_type == "signal":
        return SignalHandler(config)
    else:
        raise ValueError(f"Unknown handler type: {handler_type}. Supported types: 'matrix', 'signal'")


async def main() -> None:
    args = docopt(__doc__)
    # Load config
    config_path = args["CONFIG"]

    with open(config_path) as config_file:
        config = json.load(config_file)

    # Create the appropriate handler based on config type
    handler = create_handler(config)
    
    try:
        # Connect the handler
        await handler.connect()
        
        log.info("create listener")
        
        # Start the recent changes checker
        asyncio.create_task(
            check_recent_changes(handler, config)
        )
        
        # Run the handler's main loop
        await handler.run()
    finally:
        await handler.close()


# asyncio.get_event_loop().run_until_complete(main())
sys.exit(asyncio.run(main()))
