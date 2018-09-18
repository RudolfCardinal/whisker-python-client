#!/usr/bin/env python
# whisker/api.py

"""
===============================================================================

    Copyright (C) 2011-2018 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of the Whisker Python client library.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============================================================================

**Whisker API constants and functions.**

"""

from contextlib import contextmanager
from enum import Enum, unique
import logging
import re
from typing import Any, Callable, Generator, List, Optional, Tuple

from whisker.callback import CallbackHandler
from whisker.exceptions import WhiskerCommandFailed

log = logging.getLogger(__name__)

# =============================================================================
# API constants
# =============================================================================

# -----------------------------------------------------------------------------
# Interface basics
# -----------------------------------------------------------------------------

EOL = '\n'
# Whisker sends (and accepts) LF between responses, and we are operating in the
# str (not bytes) domain; see below re readAll().
EOL_LEN = len(EOL)

ENCODING = 'ascii'

# -----------------------------------------------------------------------------
# Server -> client
# -----------------------------------------------------------------------------

IMMPORT_REGEX = re.compile(r"^ImmPort: (\d+)")
CODE_REGEX = re.compile(r"^Code: (\w+)")
TIMESTAMP_REGEX = re.compile(r"^(.*)\s+\[(\d+)\]$")

RESPONSE_SUCCESS = "Success"
RESPONSE_FAILURE = "Failure"
PING = "Ping"
PING_ACK = "PingAcknowledged"

EVENT_REGEX = re.compile(r"^Event: (.*)$")
KEY_EVENT_REGEX = re.compile(r"^KeyEvent: (.*)$")
CLIENT_MESSAGE_REGEX = re.compile(r"^ClientMessage: (\d+) (.*)$")
INFO_REGEX = re.compile(r"^Info: (.*)$")
WARNING_REGEX = re.compile(r"Warning: (.*)$")
SYNTAX_ERROR_REGEX = re.compile(r"^SyntaxError: (.*)$")
ERROR_REGEX = re.compile(r"Error: (.*)$")

EVENT_PREFIX = "Event: "
KEY_EVENT_PREFIX = "KeyEvent: "
CLIENT_MESSAGE_PREFIX = "ClientMessage: "
INFO_PREFIX = "Info: "
WARNING_PREFIX = "Warning: "
SYNTAX_ERROR_PREFIX = "SyntaxError: "
ERROR_PREFIX = "Error: "

MSG_AUTHENTICATE_CHALLENGE = "AuthenticateChallenge"
MSG_SIZE = "Size"
MSG_EXTENT = "Extent"
MSG_KEYEVENT_UP = "up"
MSG_KEYEVENT_DOWN = "down"

# -----------------------------------------------------------------------------
# Client -> server
# -----------------------------------------------------------------------------

CMD_AUDIO_CLAIM = "AudioClaim"
CMD_AUDIO_GET_SOUND_LENGTH = "AudioGetSoundLength"
CMD_AUDIO_LOAD_SOUND = "AudioLoadSound"
CMD_AUDIO_LOAD_TONE = "AudioLoadTone"
CMD_AUDIO_PLAY_FILE = "AudioPlayFile"
CMD_AUDIO_PLAY_SOUND = "AudioPlaySound"
CMD_AUDIO_RELINQUISH_ALL = "AudioRelinquishAll"
CMD_AUDIO_SET_ALIAS = "AudioSetAlias"
CMD_AUDIO_SET_SOUND_VOLUME = "AudioSetSoundVolume"
CMD_AUDIO_SILENCE_ALL_DEVICES = "AudioSilenceAllDevices"
CMD_AUDIO_SILENCE_DEVICE = "AudioSilenceDevice"
CMD_AUDIO_STOP_SOUND = "AudioStopSound"
CMD_AUDIO_UNLOAD_ALL = "AudioUnloadAll"
CMD_AUDIO_UNLOAD_SOUND = "AudioUnloadSound"
CMD_AUTHENTICATE = "Authenticate"
CMD_AUTHENTICATE_RESPONSE = "AuthenticateResponse"
CMD_CLAIM_GROUP = "ClaimGroup"
CMD_CLIENT_NUMBER = "ClientNumber"
CMD_DISPLAY_ADD_OBJECT = "DisplayAddObject"
CMD_DISPLAY_BLANK = "DisplayBlank"
CMD_DISPLAY_BRING_TO_FRONT = "DisplayBringToFront"
CMD_DISPLAY_CACHE_CHANGES = "DisplayCacheChanges"
CMD_DISPLAY_CLAIM = "DisplayClaim"
CMD_DISPLAY_CLEAR_BACKGROUND_EVENT = "DisplayClearBackgroundEvent"
CMD_DISPLAY_CLEAR_EVENT = "DisplayClearEvent"
CMD_DISPLAY_CREATE_DEVICE = "DisplayCreateDevice"
CMD_DISPLAY_CREATE_DOCUMENT = "DisplayCreateDocument"
CMD_DISPLAY_DELETE_DEVICE = "DisplayDeleteDevice"
CMD_DISPLAY_DELETE_DOCUMENT = "DisplayDeleteDocument"
CMD_DISPLAY_DELETE_OBJECT = "DisplayDeleteObject"
CMD_DISPLAY_EVENT_COORDS = "DisplayEventCoords"
CMD_DISPLAY_GET_DOCUMENT_SIZE = "DisplayGetDocumentSize"
CMD_DISPLAY_GET_OBJECT_EXTENT = "DisplayGetObjectExtent"
CMD_DISPLAY_GET_SIZE = "DisplayGetSize"
CMD_DISPLAY_KEYBOARD_EVENTS = "DisplayKeyboardEvents"
CMD_DISPLAY_RELINQUISH_ALL = "DisplayRelinquishAll"
CMD_DISPLAY_SCALE_DOCUMENTS = "DisplayScaleDocuments"
CMD_DISPLAY_SEND_TO_BACK = "DisplaySendToBack"
CMD_DISPLAY_SET_ALIAS = "DisplaySetAlias"
CMD_DISPLAY_SET_AUDIO_DEVICE = "DisplaySetAudioDevice"
CMD_DISPLAY_SET_BACKGROUND_COLOUR = "DisplaySetBackgroundColour"
CMD_DISPLAY_SET_BACKGROUND_EVENT = "DisplaySetBackgroundEvent"
CMD_DISPLAY_SET_DOCUMENT_SIZE = "DisplaySetDocumentSize"
CMD_DISPLAY_SET_EVENT = "DisplaySetEvent"
CMD_DISPLAY_SET_OBJ_EVENT_TRANSPARENCY = "DisplaySetObjectEventTransparency"
CMD_DISPLAY_SHOW_CHANGES = "DisplayShowChanges"
CMD_DISPLAY_SHOW_DOCUMENT = "DisplayShowDocument"
CMD_LINE_CLAIM = "LineClaim"
CMD_LINE_CLEAR_ALL_EVENTS = "LineClearAllEvents"
CMD_LINE_CLEAR_EVENT = "LineClearEvent"
CMD_LINE_CLEAR_EVENTS_BY_LINE = "LineClearEventsByLine"
CMD_LINE_CLEAR_SAFETY_TIMER = "LineClearSafetyTimer"
CMD_LINE_READ_STATE = "LineReadState"
CMD_LINE_RELINQUISH_ALL = "LineRelinquishAll"
CMD_LINE_SET_ALIAS = "LineSetAlias"
CMD_LINE_SET_EVENT = "LineSetEvent"
CMD_LINE_SET_SAFETY_TIMER = "LineSetSafetyTimer"
CMD_LINE_SET_STATE = "LineSetState"
CMD_LOG_CLOSE = "LogClose"
CMD_LOG_OPEN = "LogOpen"
CMD_LOG_PAUSE = "LogPause"
CMD_LOG_RESUME = "LogResume"
CMD_LOG_SET_OPTIONS = "LogSetOptions"
CMD_LOG_WRITE = "LogWrite"
CMD_PERMIT_CLIENT_MESSAGES = "PermitClientMessages"
CMD_REPORT_COMMENT = "ReportComment"
CMD_REPORT_NAME = "ReportName"
CMD_REPORT_STATUS = "ReportStatus"
CMD_REQUEST_TIME = "RequestTime"
CMD_RESET_CLOCK = "ResetClock"
CMD_SEND_TO_CLIENT = "SendToClient"
CMD_SET_MEDIA_DIRECTORY = "SetMediaDirectory"
CMD_SHUTDOWN = "Shutdown"
CMD_TEST_NETWORK_LATENCY = "TestNetworkLatency"
CMD_TIMER_CLEAR_ALL_EVENTS = "TimerClearAllEvents"
CMD_TIMER_CLEAR_EVENT = "TimerClearEvent"
CMD_TIMER_SET_EVENT = "TimerSetEvent"
CMD_TIMESTAMPS = "Timestamps"
CMD_VERSION = "Version"
CMD_VIDEO_GET_DURATION = "VideoGetDuration"
CMD_VIDEO_GET_TIME = "VideoGetTime"
CMD_VIDEO_PAUSE = "VideoPause"
CMD_VIDEO_PLAY = "VideoPlay"
CMD_VIDEO_SEEK_ABSOLUTE = "VideoSeekAbsolute"
CMD_VIDEO_SEEK_RELATIVE = "VideoSeekRelative"
CMD_VIDEO_SET_VOLUME = "VideoSetVolume"
CMD_VIDEO_STOP = "VideoStop"
CMD_VIDEO_TIMESTAMPS = "VideoTimestamps"
CMD_WHISKER_STATUS = "WhiskerStatus"

FLAG_ALIAS = "-alias"
FLAG_BACKCOLOUR = "-backcolour"
FLAG_BASELINE = "-baseline"
FLAG_BITMAP_CLIP = "-clip"
FLAG_BITMAP_STRETCH = "-stretch"
FLAG_BOTTOM = "-bottom"
FLAG_BRUSH_BACKGROUND = "-brushbackground"
FLAG_BRUSH_OPAQUE = "-brushopaque"
FLAG_BRUSH_STYLE_HATCHED = "-brushhatched"
FLAG_BRUSH_STYLE_HOLLOW = "-brushhollow"
FLAG_BRUSH_STYLE_SOLID = "-brushsolid"
FLAG_BRUSH_TRANSPARENT = "-brushtransparent"
FLAG_CENTRE = "-centre"
FLAG_CLIENTCLIENT = "-clientclient"
FLAG_COMMS = "-comms"
FLAG_DEBUG_TOUCHES = "-debugtouches"
FLAG_DIRECTDRAW = "-directdraw"
FLAG_EVENTS = "-events"
FLAG_FONT = "-font"
FLAG_HEIGHT = "-height"
FLAG_INPUT = "-input"
FLAG_KEYEVENTS = "-keyevents"
FLAG_LEFT = "-left"
FLAG_LOOP = "-loop"
FLAG_MIDDLE = "-middle"
FLAG_OUTPUT = "-output"
FLAG_PEN_COLOUR = "-pencolour"
FLAG_PEN_STYLE = "-penstyle"
FLAG_PEN_WIDTH = "-penwidth"
FLAG_POLYGON_ALTERNATE = "-alternate"
FLAG_POLYGON_WINDING = "-winding"
FLAG_PREFIX = "-prefix"
FLAG_RESET_LEAVE = "-leave"
FLAG_RESET_OFF = "-resetoff"
FLAG_RESET_ON = "-reseton"
FLAG_RESIZE = "-resize"
FLAG_RIGHT = "-right"
FLAG_SIGNATURE = "-signature"
FLAG_SUFFIX = "-suffix"
FLAG_TEXT_COLOUR = "-textcolour"
FLAG_TEXT_ITALIC = "-italic"
FLAG_TEXT_OPAQUE = "-opaque"
FLAG_TEXT_UNDERLINE = "-underline"
FLAG_TEXT_WEIGHT = "-weight"
FLAG_TOP = "-top"
FLAG_VIDEO_AUDIO = "-audio"
FLAG_VIDEO_NOAUDIO = "-noaudio"
FLAG_VIDEO_NOLOOP = "-noloop"
FLAG_VIDEO_PLAYIMMEDIATE = "-playimmediate"
FLAG_VIDEO_PLAYWHENVISIBLE = "-playwhenvisible"
FLAG_VIDEO_WAIT = "-wait"
FLAG_WIDTH = "-width"

QUOTE = '"'

VAL_ANALOGUE_EVENTTYPE_ABOVE = "above"
VAL_ANALOGUE_EVENTTYPE_ALL = "all"
VAL_ANALOGUE_EVENTTYPE_BELOW = "below"
VAL_ANALOGUE_EVENTTYPE_RANGE = "range"
VAL_BOTH = "both"
VAL_BRUSH_HATCH_BDIAGONAL = "bdiagonal"
VAL_BRUSH_HATCH_CROSS = "cross"
VAL_BRUSH_HATCH_DIAGCROSS = "diagcross"
VAL_BRUSH_HATCH_FDIAGONAL = "fdiagonal"
VAL_BRUSH_HATCH_HORIZONTAL = "horizontal"
VAL_BRUSH_HATCH_VERTICAL = "vertical"
VAL_KEYEVENT_DOWN = "down"
VAL_KEYEVENT_NONE = "none"
VAL_KEYEVENT_UP = "up"
VAL_MOUSE_DBLCLICK = "MouseDblClick"
VAL_MOUSE_DOWN = "MouseDown"
VAL_MOUSE_MOVE = "MouseMove"
VAL_MOUSE_UP = "MouseUp"
VAL_OBJTYPE_ARC = "arc"
VAL_OBJTYPE_BEZIER = "bezier"
VAL_OBJTYPE_BITMAP = "bitmap"
VAL_OBJTYPE_CAMCOGQUADPATTERN = "camcogquadpattern"
VAL_OBJTYPE_CHORD = "chord"
VAL_OBJTYPE_ELLIPSE = "ellipse"
VAL_OBJTYPE_LINE = "line"
VAL_OBJTYPE_PIE = "pie"
VAL_OBJTYPE_POLYGON = "polygon"
VAL_OBJTYPE_RECTANGLE = "rectangle"
VAL_OBJTYPE_ROUNDRECT = "roundrect"
VAL_OBJTYPE_TEXT = "text"
VAL_OBJTYPE_VIDEO = "video"
VAL_OFF = "off"
VAL_ON = "on"
VAL_PEN_DASH = "dash"
VAL_PEN_DASH_DOT = "dashdot"
VAL_PEN_DASH_DOT_DOT = "dashdotdot"
VAL_PEN_DOT = "dot"
VAL_PEN_INSIDE_FRAME = "insideframe"
VAL_PEN_NULL = "null"
VAL_PEN_SOLID = "solid"
VAL_TONE_SAWTOOTH = "sawtooth"
VAL_TONE_SINE = "sine"
VAL_TONE_SQUARE = "square"
VAL_TONE_TONE = "tone"
VAL_TOUCH_DOWN = "TouchDown"
VAL_TOUCH_MOVE = "TouchMove"
VAL_TOUCH_UP = "TouchUp"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
ColourType = Tuple[int, int, int]

PointType = Tuple[int, int]
SizeType = Tuple[int, int]


@unique
class ResetState(Enum):
    input = 0
    on = 1
    off = 2
    leave = 3


@unique
class LineEventType(Enum):
    on = 1
    off = 2
    both = 3


@unique
class SafetyState(Enum):
    off = 0
    on = 1


@unique
class DocEventType(Enum):
    mouse_down = 1
    mouse_up = 2
    mouse_double_click = 3
    mouse_move = 4
    touch_down = 5
    touch_up = 6
    touch_move = 7


@unique
class KeyEventType(Enum):
    none = 0
    down = 1
    up = 2
    both = 3


@unique
class ToneType(Enum):
    sine = 1
    sawtooth = 2
    square = 3
    tone = 4


@unique
class VerticalAlign(Enum):
    top = 0
    middle = 1
    bottom = 2


@unique
class TextVerticalAlign(Enum):
    top = 0
    middle = 1
    bottom = 2
    baseline = 3


@unique
class HorizontalAlign(Enum):
    left = 0
    centre = 1
    right = 2


@unique
class TextHorizontalAlign(Enum):
    left = 0
    centre = 1
    right = 2


@unique
class VideoPlayMode(Enum):
    wait = 0
    immediate = 1
    when_visible = 2


@unique
class PenStyle(Enum):
    solid = 0
    dash = 1
    dot = 2
    dash_dot = 3
    dash_dot_dot = 4
    null = 5
    inside_frame = 6


@unique
class BrushStyle(Enum):
    hollow = 0
    solid = 1
    hatched = 2


@unique
class BrushHatchStyle(Enum):
    horizontal = 0  # . -----
    vertical = 1  # .  |||||
    fdiagonal = 2  # . \\\\\ (see WinGDI.h)
    bdiagonal = 3  # . ///// (see WinGDI.h)
    cross = 4  # .     +++++
    diagcross = 5  # . xxxxx


VIDEO_PLAYMODE_FLAGS = {
    VideoPlayMode.wait: FLAG_VIDEO_WAIT,
    VideoPlayMode.immediate: FLAG_VIDEO_PLAYIMMEDIATE,
    VideoPlayMode.when_visible: FLAG_VIDEO_PLAYWHENVISIBLE,
}
VALIGN_FLAGS = {
    VerticalAlign.top: FLAG_TOP,
    VerticalAlign.middle: FLAG_MIDDLE,
    VerticalAlign.bottom: FLAG_BOTTOM,
}
HALIGN_FLAGS = {
    HorizontalAlign.left: FLAG_LEFT,
    HorizontalAlign.centre: FLAG_CENTRE,
    HorizontalAlign.right: FLAG_RIGHT,
}
TEXT_VALIGN_FLAGS = {
    TextVerticalAlign.top: FLAG_TOP,
    TextVerticalAlign.middle: FLAG_MIDDLE,
    TextVerticalAlign.bottom: FLAG_BOTTOM,
    TextVerticalAlign.baseline: FLAG_BASELINE,
}
TEXT_HALIGN_FLAGS = {
    TextHorizontalAlign.left: FLAG_LEFT,
    TextHorizontalAlign.centre: FLAG_CENTRE,
    TextHorizontalAlign.right: FLAG_RIGHT,
}
LINE_RESET_FLAGS = {
    ResetState.input: "",
    ResetState.on: FLAG_RESET_ON,
    ResetState.off: FLAG_RESET_OFF,
    ResetState.leave: FLAG_RESET_LEAVE,
}
AUDIO_TONE_TYPES = {
    ToneType.sine: VAL_TONE_SINE,
    ToneType.sawtooth: VAL_TONE_SAWTOOTH,
    ToneType.square: VAL_TONE_SQUARE,
    ToneType.tone: VAL_TONE_TONE,
}
LINE_SAFETY_STATES = {
    SafetyState.on: VAL_ON,
    SafetyState.off: VAL_OFF,
}
LINE_EVENT_TYPES = {
    LineEventType.on: VAL_ON,
    LineEventType.off: VAL_OFF,
    LineEventType.both: VAL_BOTH,
}
DOC_EVENT_TYPES = {
    DocEventType.mouse_down: VAL_MOUSE_DOWN,
    DocEventType.mouse_up: VAL_MOUSE_UP,
    DocEventType.mouse_double_click: VAL_MOUSE_DBLCLICK,
    DocEventType.mouse_move: VAL_MOUSE_MOVE,
    DocEventType.touch_down: VAL_TOUCH_DOWN,
    DocEventType.touch_up: VAL_TOUCH_UP,
    DocEventType.touch_move: VAL_TOUCH_MOVE,
}
KEY_EVENT_TYPES = {
    KeyEventType.none: VAL_KEYEVENT_NONE,
    KeyEventType.down: VAL_KEYEVENT_DOWN,
    KeyEventType.up: VAL_KEYEVENT_UP,
    KeyEventType.both: VAL_BOTH,
}
PEN_STYLE_FLAGS = {
    PenStyle.solid: VAL_PEN_SOLID,
    PenStyle.dash: VAL_PEN_DASH,
    PenStyle.dot: VAL_PEN_DOT,
    PenStyle.dash_dot: VAL_PEN_DASH_DOT,
    PenStyle.dash_dot_dot: VAL_PEN_DASH_DOT_DOT,
    PenStyle.null: VAL_PEN_NULL,
    PenStyle.inside_frame: VAL_PEN_INSIDE_FRAME,
}
BRUSH_STYLE_FLAGS = {
    BrushStyle.hollow: FLAG_BRUSH_STYLE_HOLLOW,
    BrushStyle.solid: FLAG_BRUSH_STYLE_SOLID,
    BrushStyle.hatched: FLAG_BRUSH_STYLE_HATCHED,
}
BRUSH_HATCH_VALUES = {
    BrushHatchStyle.vertical: VAL_BRUSH_HATCH_VERTICAL,
    BrushHatchStyle.fdiagonal: VAL_BRUSH_HATCH_FDIAGONAL,
    BrushHatchStyle.horizontal: VAL_BRUSH_HATCH_HORIZONTAL,
    BrushHatchStyle.bdiagonal: VAL_BRUSH_HATCH_BDIAGONAL,
    BrushHatchStyle.cross: VAL_BRUSH_HATCH_CROSS,
    BrushHatchStyle.diagcross: VAL_BRUSH_HATCH_DIAGCROSS,
}


# =============================================================================
# Helper functions
# =============================================================================

def _on_val(on: bool) -> str:
    """
    Converts a boolean to Whisker's on/off value strings.
    """
    return VAL_ON if on else VAL_OFF


def split_timestamp(msg: str) -> Tuple[str, Optional[int]]:
    """
    Splits a Whisker message into the message proper and a server timestamp.

    Args:
        msg: a Whisker message that potentially has a timestamp

    Returns:
        tuple: ``(msg, timestamp)`` where ``timestamp`` may be ``None``

    """
    try:
        m = TIMESTAMP_REGEX.match(msg)
        mainmsg = m.group(1)
        timestamp = int(m.group(2))
        return mainmsg, timestamp
    except (TypeError, AttributeError, ValueError):
        return msg, None


def on_off_to_boolean(msg: str) -> bool:
    """
    Convert's Whisker's on/off value strings to boolean.
    """
    return True if msg == VAL_ON else False


def s_to_ms(time_seconds: float) -> int:
    """
    Converts seconds to milliseconds.
    """
    return int(time_seconds * 1000)


def min_to_ms(time_minutes: float) -> int:
    """
    Converts minutes to milliseconds.
    """
    return int(time_minutes * 60000)


def quote(string: str) -> str:
    """
    Quotes a string. **Suboptimal:** doesn't escape quotes.
    """
    return QUOTE + string + QUOTE


def msg_from_args(*args) -> str:
    """
    Converts its arguments, which may be of any type, to strings (via
    :func:`str`). Then joins the truthy ones them with spaces to make a
    command.
    """
    strings = [str(x) for x in args if x is not None]
    return " ".join(x for x in strings if x)


def is_ducktype_colour(colour: Any) -> bool:
    """
    Does the parameter look like a colour ``(red, green blue)`` tuple,
    with values for each in the range 0-255?
    """
    try:
        assert len(colour) == 3
        (r, g, b) = colour
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255
        return True
    except (TypeError, AssertionError):
        return False


def assert_ducktype_colour(colour: Any) -> None:
    """
    If the parameter does not pass the test :func:`is_ducktype_colour`,
    raise :exc:`ValueError`.
    """
    if not is_ducktype_colour(colour):
        raise ValueError(
            "Bad colour: must be (R, G, B) tuple. Was: {}".format(colour))


def is_ducktype_pos(pos: Any) -> bool:
    """
    Does the parameter look like a position ``(x, y)`` tuple,
    with values that can be made numeric?
    """
    try:
        assert len(pos) == 2
        (x, y) = [float(val) for val in pos]
        assert x is not None and y is not None
        return True
    except (TypeError, ValueError, AssertionError):
        return False


def assert_ducktype_pos(pos: Any) -> None:
    """
    If the parameter does not pass the test :func:`is_ducktype_pos`,
    raise :exc:`ValueError`.
    """
    if not is_ducktype_pos(pos):
        raise ValueError(
            "Bad position: must be (X, Y) tuple. Was: {}".format(pos))


def is_ducktype_int(x: Any) -> bool:
    """
    Does the parameter look like an integer?
    """
    try:
        return int(x) == float(x)
    except (TypeError, ValueError):
        return False


def is_ducktype_nonnegative_int(x: Any) -> bool:
    """
    Does the parameter look like an integer that is 0 or greater?
    """
    return is_ducktype_int(x) and int(x) >= 0


class Rectangle(object):
    """
    Represents a Whisker Rectangle graphics object.

    The origin is at the top left, as per Whisker.
    """
    def __init__(self, left: int, top: int,
                 width: int = None, height: int = None,
                 right: int = None, bottom: int = None) -> None:
        if width is None and right is None:
            raise ValueError("Bad rectangle width/right specification")
        if height is None and bottom is None:
            raise ValueError("Bad rectangle height/bottom specification")
        if width is None:
            if left > right:
                (left, right) = (right, left)
            self._width = right - left
        else:
            self._width = width
        if height is None:
            if top > bottom:
                (top, bottom) = (bottom, top)
            self._height = bottom - top
        else:
            self._height = height
        self._left = left
        self._top = top

    @property
    def left(self) -> int:
        return self._left

    @property
    def top(self) -> int:
        return self._top

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def right(self) -> int:
        return self._left + self._width

    @property
    def bottom(self) -> int:
        return self._top + self._height

    @property
    def centre_x(self) -> int:
        return int(self._left + self._width / 2)

    @property
    def centre_y(self) -> int:
        return int(self._top + self._height / 2)

    @property
    def centre(self) -> PointType:
        return self.centre_x, self.centre_y

    @property
    def left_top(self) -> PointType:
        return self._left, self.top

    @property
    def right_bottom(self) -> PointType:
        return self.right, self.bottom


class Pen(object):
    """
    Represents a Whisker Pen graphics object.
    """
    def __init__(self,
                 width: int = 1,
                 colour: ColourType = WHITE,
                 style: PenStyle = PenStyle.solid) -> None:
        assert_ducktype_colour(colour)
        assert isinstance(style, PenStyle)
        self.style = style
        self.width = width
        self.colour = colour

    @property
    def whisker_option_string(self) -> str:
        args = [
            FLAG_PEN_COLOUR, self.colour[0], self.colour[1], self.colour[2],
            FLAG_PEN_WIDTH, self.width,
            FLAG_PEN_STYLE, PEN_STYLE_FLAGS[self.style],
        ]
        return msg_from_args(*args)


class Brush(object):
    """
    Represents a Whisker Brush graphics object.
    """
    def __init__(self,
                 colour: ColourType = WHITE,
                 bg_colour: ColourType = BLACK,
                 opaque: bool = True,
                 style: BrushStyle = BrushStyle.solid,
                 hatch_style: BrushHatchStyle = BrushHatchStyle.cross) -> None:
        assert_ducktype_colour(colour)
        assert_ducktype_colour(bg_colour)
        assert isinstance(style, BrushStyle)
        assert isinstance(hatch_style, BrushHatchStyle)
        self.colour = colour
        self.bg_colour = bg_colour
        self.opaque = opaque
        self.style = style
        self.hatch_style = hatch_style

    @property
    def whisker_option_string(self) -> str:
        args = [BRUSH_STYLE_FLAGS[self.style]]  # type: List[Any]
        if self.style == BrushStyle.solid:
            args.extend(self.colour)
        elif self.style == BrushStyle.hatched:
            args.append(BRUSH_HATCH_VALUES[self.hatch_style])
            args.extend(self.colour)
            if self.opaque:
                args.append(FLAG_BRUSH_OPAQUE)
                args.append(FLAG_BRUSH_BACKGROUND)
                args.extend(self.bg_colour)
            else:
                args.append(FLAG_BRUSH_TRANSPARENT)
        return msg_from_args(*args)


# =============================================================================
# WhiskerApi
# =============================================================================

class WhiskerApi(object):
    """
    Whisker API handler.

    Distinct from any particular network/threading model, so all can use it
    (e.g. by inheritance), but hooks in to whichever you choose.
    """
    def __init__(self,
                 whisker_immsend_get_reply_fn: Callable[..., str],
                 sysevent_prefix: str = "sys_",
                 **kwargs) -> None:
        """
        Args:
            whisker_immsend_get_reply_fn:
                A function that must take arguments ``*args``, join stringified
                versions of them using a space as the separator, and send them
                to the Whisker server via the immediate socket, returning the
                string that the server sent back.
            sysevent_prefix:
                string to prefix system events with
            kwargs
                used in case of mixin inheritance
        """
        super().__init__(**kwargs)
        self._immsend_get_reply = whisker_immsend_get_reply_fn
        self.sysevent_prefix = sysevent_prefix
        self.sysevent_counter = 0
        self.callback_handler = CallbackHandler()

    # -------------------------------------------------------------------------
    # Internal derived comms
    # -------------------------------------------------------------------------

    def _immresp(self, *args) -> str:
        reply = self._immsend_get_reply(*args)
        (reply, whisker_timestamp) = split_timestamp(reply)
        return reply

    def _immbool(self, *args) -> bool:
        reply = self._immresp(*args)
        return reply == RESPONSE_SUCCESS

    def _immresp_with_timestamp(self, *args) -> Tuple[str, Optional[int]]:
        reply = self._immsend_get_reply(*args)
        (reply, whisker_timestamp) = split_timestamp(reply)
        return reply, whisker_timestamp

    # -------------------------------------------------------------------------
    # Front-end functions for these
    # -------------------------------------------------------------------------

    def get_command_boolean(self, *args) -> bool:
        """
        Return a boolean answer from an immediate socket command.
        """
        return self._immbool(*args)

    def command(self, *args) -> bool:
        """
        Return a boolean answer from an immediate socket command.
        """
        return self._immbool(*args)

    def command_exc(self, *args) -> None:
        """
        Send a command; if it fails, raise :exc:`WhiskerCommandFailed`.
        """
        if not self._immbool(*args):
            raise WhiskerCommandFailed(msg_from_args(*args))

    def get_response(self, *args) -> str:
        """
        Return the answer from an immediate socket command.
        """
        return self._immresp(*args)

    def get_response_with_timestamp(self, *args) -> Tuple[str, Optional[int]]:
        """
        Return the answer from an immediate socket command, with a timestamp.
        """
        return self._immresp_with_timestamp(*args)

    # -------------------------------------------------------------------------
    # Custom event handling, e.g. for line flashing
    # -------------------------------------------------------------------------

    def get_new_sysevent(self, *args) -> str:
        """
        Make a new system event name.
        """
        self.sysevent_counter += 1
        return self.sysevent_prefix + "_".join(
            str(x) for x in [self.sysevent_counter] + list(args)
        ).replace(" ", "")

    def process_backend_event(self, event: str) -> bool:
        """
        Process an through the system event handler.

        Returns ``True`` if the backend API has dealt with the event and it
        doesn't need to go to the main behavioural task.
        """
        n_called, swallow_event = self.callback_handler.process_event(event)
        return (
            (n_called > 0 and swallow_event) or
            event.startswith(self.sysevent_prefix)
        )

    def send_after_delay(self, delay_ms: int, msg: str,
                         event: str = '') -> None:
        """
        Sets a Whisker timer so we'll be called back after a delay, and then
        send the command.

        Args:
            delay_ms: delay in ms
            msg: message to send after the delay
            event: optional Whisker event name (a default will be usd if none
                is provided)
        """
        event = event or self.get_new_sysevent("send", msg)
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, self._immsend_get_reply, [msg])

    def call_after_delay(self,
                         delay_ms: int,
                         callback: Callable[..., None],
                         args: List[Any] = None,
                         kwargs: List[Any] = None,
                         event: str = '') -> None:
        """
        Sets a Whisker timer so we'll be called back after a delay, and then
        call a Python function.

        Args:
            delay_ms: delay in ms
            callback: function to call back
            args: positional arguments to ``callback``
            kwargs: keyword arguments to ``callback``
            event: optional Whisker event name (a default will be usd if none
                is provided)
        """
        args = args or []
        kwargs = kwargs or {}
        event = event or self.get_new_sysevent("call")
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, callback, args, kwargs)

    def call_on_event(self,
                      event: str,
                      callback: Callable[..., None],
                      args: List[Any] = None,
                      kwargs: List[Any] = None,
                      swallow_event: bool = False) -> None:
        """
        Tells the callback handler to call a function whenever we receive a
        particular event from Whisker.

        Args:
            event: Whisker event name
            callback: function to call back
            args: positional arguments to ``callback``
            kwargs: keyword arguments to ``callback``
            swallow_event: make the API swallow the event, so it's not seen by
                our client task?
        """
        args = args or []
        kwargs = kwargs or {}
        self.callback_handler.add_persistent(event, callback, args, kwargs,
                                             swallow_event=swallow_event)

    def clear_event_callback(self,
                             event: str,
                             callback: Callable[..., None] = None) -> None:
        """
        Cancels a callback.

        Args:
            event: Whisker event name
            callback: callback function to remove from callback list
        """
        self.callback_handler.remove(event, callback=callback)

    def clear_all_callbacks(self) -> None:
        """
        Cancel all callbacks.
        """
        self.callback_handler.clear()

    def debug_callbacks(self) -> None:
        """
        Display our callback settings to the Python log.
        """
        self.callback_handler.debug()

    # -------------------------------------------------------------------------
    # Line flashing
    # -------------------------------------------------------------------------

    def flash_line_pulses(self,
                          line: str,
                          count: int,
                          on_ms: int,
                          off_ms: int,
                          on_at_rest: bool = False) -> int:
        """
        Flash a line for a specified number of pulses.

        Args:
            line: Whisker line number/name
            count: number of flashes
            on_ms: time spent in the "on" phase of the cycle, in ms
            off_ms: time spent in the "off" phase of the cycle, in ms
            on_at_rest: is the line on at rest, so we count "off flashes"?
                The default, with this ``False``, is to assume the line is off
                at rest and we count "on" flashes.

        Returns:
            the total duration of the flashing sequence, in ms

        """
        assert count > 0
        # Generally better to ping-pong the events, rather than line them up
        # in advance, in case the user specifies very rapid oscillation that
        # exceeds the network bandwidth, or something; better to be slow than
        # to garbage up the sequence.
        if on_at_rest:
            # Currently at rest = on.
            # For 4 flashes:
            # OFF .. ON .... OFF .. ON .... OFF .. ON .... OFF .. ON
            on_now = False
            timing_sequence = [off_ms] + (count - 1) * [on_ms, off_ms]
        else:
            # Currently at rest = off.
            # For 4 flashes:
            # ON .... OFF .. ON .... OFF .. ON .... OFF .. ON .... OFF
            on_now = True
            timing_sequence = [on_ms] + (count - 1) * [off_ms, on_ms]
        total_duration_ms = sum(timing_sequence)
        self.flash_line_ping_pong(line, on_now, timing_sequence)
        return total_duration_ms

    def flash_line_ping_pong(self,
                             line: str,
                             on_now: bool,
                             timing_sequence: List[int]) -> None:
        """
        Internal function used by :func:`flash_line_pulses`.

        Args:
            line: Whisker line number/name
            on_now: switch it on now (otherwise off)?
            timing_sequence: sequence of [off]/on/off/... times still to do,
                in ms
        """
        self.line_on(line) if on_now else self.line_off(line)
        if not timing_sequence:
            return
        delay_ms = timing_sequence[0]
        timing_sequence = timing_sequence[1:]
        event = self.get_new_sysevent(line, "off" if on_now else "on")
        self.call_after_delay(delay_ms, self.flash_line_ping_pong,
                              args=[line, not on_now, timing_sequence],
                              event=event)

    # -------------------------------------------------------------------------
    # Whisker command set: comms, misc
    # -------------------------------------------------------------------------

    def timestamps(self, on: bool) -> bool:
        """
        Whisker command: turn timestamps on/off.
        """
        return self._immbool(CMD_TIMESTAMPS, _on_val(on))

    def reset_clock(self) -> bool:
        """
        Whisker command: reset server clock.
        """
        return self._immbool(CMD_RESET_CLOCK)

    def get_server_version(self) -> str:
        """
        Whisker command: get the server version, as a string.
        """
        return self._immresp(CMD_VERSION)

    def get_server_version_numeric(self) -> float:
        """
        Whisker command: get the server version, as a float.
        """
        return float(self.get_server_version())

    def get_server_time_ms(self) -> int:
        """
        Whisker command: get the time on the server, from its millisecond
        clock.
        """
        return int(self._immresp(CMD_REQUEST_TIME))

    def get_client_number(self) -> int:
        """
        Whisker command: get the client number for our client.
        """
        return int(self._immresp(CMD_CLIENT_NUMBER))

    def permit_client_messages(self, permit: bool) -> bool:
        """
        Whisker command: enable/disable client messages.
        """
        return self._immbool(CMD_PERMIT_CLIENT_MESSAGES, _on_val(permit))

    def send_to_client(self, client_num: int, *args) -> bool:
        """
        Whisker command: send a message to another client.
        """
        return self._immbool(CMD_SEND_TO_CLIENT, client_num,
                             msg_from_args(*args))

    def set_media_directory(self, directory: str) -> bool:
        """
        Whisker command: set the server's media directory.
        """
        return self._immbool(CMD_SET_MEDIA_DIRECTORY, quote(directory))

    def report_name(self, *args) -> bool:
        """
        Whisker command: tell the server our name.
        """
        return self._immbool(CMD_REPORT_NAME, msg_from_args(*args))
        # quotes not necessary

    def report_status(self, *args) -> bool:
        """
        Whisker command: tell the server our status.
        """
        return self._immbool(CMD_REPORT_STATUS, msg_from_args(*args))
        # quotes not necessary

    def report_comment(self, *args) -> bool:
        """
        Whisker command: tell the server our comment.
        """
        return self._immbool(CMD_REPORT_COMMENT, msg_from_args(*args))
        # quotes not necessary

    def get_network_latency_ms(self) -> Optional[int]:
        """
        Whisker command: test the network latency.
        """
        reply = self._immresp(CMD_TEST_NETWORK_LATENCY)
        if reply != PING:
            return None
        try:
            reply = self._immresp(PING_ACK)
            return int(reply)
        except (TypeError, ValueError):
            return None

    def ping(self) -> bool:
        """
        Whisker command: ping the server.
        """
        reply = self._immresp(PING)
        success = reply == PING_ACK
        return success

    def shutdown(self) -> bool:
        """
        Whisker command: shutdown.
        """
        return self._immbool(CMD_SHUTDOWN)

    def authenticate_get_challenge(self, package: str,
                                   client_name: str) -> Optional[str]:
        """
        Whisker command: ask the server for an authentication challenge, using
        a particular software package name and client name.
        """
        reply = self._immresp(CMD_AUTHENTICATE, package, client_name)
        if not reply.startswith(MSG_AUTHENTICATE_CHALLENGE + " "):
            return None
        challenge = reply.split()[1]
        return challenge

    def authenticate_provide_response(self, response: str) -> bool:
        """
        Whisker command: respond to the server's authentication challenge with
        an appropriate cryptographic answer.
        """
        return self._immbool(CMD_AUTHENTICATE_RESPONSE, response)

    # -------------------------------------------------------------------------
    # Whisker command set: logs
    # -------------------------------------------------------------------------

    def log_open(self, filename: str) -> bool:
        """
        Whisker command: open a log file.
        """
        return self._immbool(CMD_LOG_OPEN, quote(filename))

    def log_set_options(self,
                        events: bool = True,
                        key_events: bool = True,
                        client_client: bool = True,
                        comms: bool = False,
                        signature: bool = True) -> bool:
        """
        Whisker command: set log file options.

        Args:
            events: log events?
            key_events: log keyboard events?
            client_client: log client/client communications?
            comms: log comms?
            signature: sign the log digitally?
        """
        return self._immbool(
            CMD_LOG_SET_OPTIONS,
            FLAG_EVENTS, _on_val(events),
            FLAG_KEYEVENTS, _on_val(key_events),
            FLAG_CLIENTCLIENT, _on_val(client_client),
            FLAG_COMMS, _on_val(comms),
            FLAG_SIGNATURE, _on_val(signature),
        )

    def log_pause(self) -> bool:
        """
        Whisker command: pause logging.
        """
        return self._immbool(CMD_LOG_PAUSE)

    def log_resume(self) -> bool:
        """
        Whisker command: resume logging.
        """
        return self._immbool(CMD_LOG_RESUME)

    def log_write(self, *args) -> bool:
        """
        Whisker command: write a message to the log.
        """
        return self._immbool(CMD_LOG_WRITE, msg_from_args(*args))

    def log_close(self) -> bool:
        """
        Whisker command: close the log.
        """
        return self._immbool(CMD_LOG_CLOSE)

    # -------------------------------------------------------------------------
    # Whisker command set: timers
    # -------------------------------------------------------------------------

    def timer_set_event(self, event: str, duration_ms: int,
                        reload_count: int = 0) -> bool:
        """
        Whisker command: set a timer.

        Args:
            event: event name
            duration_ms: timer duration (ms)
            reload_count: ``0`` for no reloads, a positive integer for a
                specified number of reloads, ``-1`` for infinite reloads.

        Returns:
            success?
        """
        return self._immbool(CMD_TIMER_SET_EVENT, duration_ms, reload_count,
                             event)

    def timer_clear_event(self, event: str) -> bool:
        """
        Whisker command: clear (cancel) a named timer.
        """
        return self._immbool(CMD_TIMER_CLEAR_EVENT, event)

    def timer_clear_all_events(self) -> bool:
        """
        Whisker command: clear (cancel) all timers.
        """
        return self._immbool(CMD_TIMER_CLEAR_ALL_EVENTS)

    # -------------------------------------------------------------------------
    # Whisker command set: claiming, relinquishing
    # -------------------------------------------------------------------------

    def claim_group(self, group: str, prefix: str = "",
                    suffix: str = "") -> bool:
        """
        Whisker command: claim a device group

        Args:
            group: group name
            prefix: prefix to apply to all device names in the group, when
                creating the alias
            suffix: suffix to apply to all device names in the group, when
                creating the alias

        Returns:
            success?

        """
        args = [CMD_CLAIM_GROUP, group]
        if prefix:
            args += [FLAG_PREFIX, prefix]
        if suffix:
            args += [FLAG_SUFFIX, suffix]
        return self._immbool(*args)

    def claim_line(self,
                   number: int = None,
                   group: str = None,
                   device: str = None,
                   output: bool = False,
                   reset_state: ResetState = ResetState.leave,
                   alias: str = "") -> bool:
        """
        Whisker command: claim a digital I/O line.

        Args:
            number: line number, for numerical method
            group: group name, for named method
            device: device name, for named method
            output: output line? (If not: input line.)
            reset_state: if/how to reset this line when the client disconnects
            alias: alias to apply

        Returns:
            success?

        """
        assert (
            (is_ducktype_nonnegative_int(number) or (group and device)) and
            not (number is not None and group)
        ), "Specify number [integer >= 0] OR (group AND device)"
        assert isinstance(reset_state, ResetState)
        args = [CMD_LINE_CLAIM]  # type: List[Any]
        if number is not None:
            args.append(number)
        else:
            args.extend([group, device])
        args.extend([
            FLAG_OUTPUT if output else FLAG_INPUT,
            LINE_RESET_FLAGS[ResetState.input if not output else reset_state]
        ])
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def relinquish_all_lines(self) -> bool:
        """
        Whisker command: relinquish all lines.
        """
        return self._immbool(CMD_LINE_RELINQUISH_ALL)

    def line_set_alias(self, line: str, alias: str) -> bool:
        """
        Whisker command: adds an alias for a line.

        Args:
            line: line name/number
            alias: new alias to apply

        Returns:
            success?

        """
        return self._immbool(CMD_LINE_SET_ALIAS, line, alias)

    def claim_audio(self, number: int = None, group: str = None,
                    device: str = None, alias: str = "") -> bool:
        """
        Whisker command: claim an audio device.

        Args:
            number: device number, for numerical method
            group: group name, for named method
            device: device name within group, for named method
            alias: alias to apply

        Returns:
            success?

        """
        assert (
            (is_ducktype_nonnegative_int(number) or (group and device)) and
            not (number is not None and group)
        ), "Specify number [integer >= 0] OR (group AND device)"
        args = [CMD_AUDIO_CLAIM]  # type: List[Any]
        if number is not None:
            args.append(number)
        else:
            args.extend([group, device])
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def audio_set_alias(self, from_: str, to: str) -> bool:
        """
        Whisker command: adds an alias for an audio device.

        Args:
            from_: audio device name/number
            to: new alias to apply

        Returns:
            success?

        """
        return self._immbool(CMD_AUDIO_SET_ALIAS, from_, to)

    def relinquish_all_audio(self) -> bool:
        """
        Whisker command: relinquish all audio devices.
        """
        return self._immbool(CMD_AUDIO_RELINQUISH_ALL)

    def claim_display(self, number: int = None, group: str = None,
                      device: str = None, alias: str = "") -> bool:
        """
        Whisker command: claim a dsplay device

        Args:
            number: device number, for numerical method
            group: group name, for named method
            device: device name within group, for named method
            alias: alias to apply

        Returns:
            success?

        Autocreating debug views is not supported (see C++ WhiskerClientLib).

        """
        assert (
            (is_ducktype_nonnegative_int(number) or (group and device)) and
            not (number is not None and group)
        ), "Specify number [integer >= 0] OR (group AND device)"
        args = [CMD_DISPLAY_CLAIM]  # type: List[Any]
        if number is not None:
            args.append(number)
        else:
            args.extend([group, device])
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def display_set_alias(self, from_: str, to: str) -> bool:
        """
        Whisker command: adds an alias for a display device.

        Args:
            from_: audio device name/number
            to: new alias to apply

        Returns:
            success?

        """
        return self._immbool(CMD_DISPLAY_SET_ALIAS, from_, to)

    def relinquish_all_displays(self) -> bool:
        """
        Whisker command: relinquish all display devices.
        """
        return self._immbool(CMD_DISPLAY_RELINQUISH_ALL)

    def display_create_device(self, name: str, resize: bool = True,
                              directdraw: bool = True,
                              rectangle: Rectangle = None,
                              debug_touches: bool = False) -> bool:
        """
        Whisker command: create a new display device (window).

        Args:
            name: display name
            resize: may the window be resized?
            directdraw: use DirectDraw for speed?
            rectangle: initial size of the window
            debug_touches: if ``True``, touches will be shown on all documents
                displayed on the device

        Returns:
            success?

        """
        args = [
            CMD_DISPLAY_CREATE_DEVICE,
            name,
            FLAG_RESIZE, _on_val(resize),
            FLAG_DIRECTDRAW, _on_val(directdraw),
        ]  # type: List[Any]
        if rectangle:
            args.extend([
                rectangle.left,
                rectangle.top,
                rectangle.width,
                rectangle.height
            ])
        if debug_touches:
            args.append(FLAG_DEBUG_TOUCHES)
        return self._immbool(*args)

    def display_delete_device(self, device: str) -> bool:
        """
        Whisker command: deletes a display device that you've created with
        :func:`display_create_device`.
        """
        return self._immbool(CMD_DISPLAY_DELETE_DEVICE, device)

    # -------------------------------------------------------------------------
    # Whisker command set: lines
    # -------------------------------------------------------------------------

    def line_set_state(self, line: str, on: bool) -> bool:
        """
        Whisker command: turns a digital output line on/off.
        """
        return self._immbool(CMD_LINE_SET_STATE, line, _on_val(on))

    def line_read_state(self, line: str) -> Optional[bool]:
        """
        Whisker command: reads the state of a digital I/O line.

        Args:
            line: line number/name

        Returns:
            ``True`` for on, ``False`` for off, ``None`` for "problem"

        """
        reply = self._immresp(CMD_LINE_READ_STATE, line)
        if reply == VAL_ON:
            return True
        elif reply == VAL_OFF:
            return False
        else:
            return None

    def line_set_event(self, line: str, event: str,
                       event_type: LineEventType = LineEventType.on) -> bool:
        """
        Whisker command: sets an event for a digital I/O line transition.

        Args:
            line: line number/name
            event: event name to create
            event_type: fire event upon on transitions, off transitions,
                or both?

        Returns:
            success?

        """
        assert isinstance(event_type, LineEventType)
        return self._immbool(CMD_LINE_SET_EVENT, line,
                             LINE_EVENT_TYPES[event_type], event)

    def line_clear_event(self, event: str) -> bool:
        """
        Whisker command: clear (cancel) a line event or events by name.
        """
        return self._immbool(CMD_LINE_CLEAR_EVENT, event)

    def line_clear_event_by_line(self, line: str,
                                 event_type: LineEventType) -> bool:
        """
        Whisker command: clear (cancel) a line event by line number/name
        and transition type.
        """
        assert isinstance(event_type, LineEventType)
        return self._immbool(CMD_LINE_CLEAR_EVENTS_BY_LINE, line,
                             LINE_EVENT_TYPES[event_type])

    def line_clear_all_events(self) -> bool:
        """
        Whisker command: clear (cancel) all line events.
        """
        return self._immbool(CMD_LINE_CLEAR_ALL_EVENTS)

    def line_set_safety_timer(self, line: str, time_ms: int,
                              safety_state: SafetyState) -> bool:
        """
        Whisker command: set a safety timer on a line.
        If the client doesn't use this line for a while, the safety system
        will kick in.

        Args:
            line: line number/name
            time_ms: how long after the client's last action with this line
                before we consider the line to be being neglected (ms)?
            safety_state: turn it off or on after it's been neglected?

        Returns:
            success?

        """
        assert isinstance(safety_state, SafetyState)
        return self._immbool(CMD_LINE_SET_SAFETY_TIMER, line, time_ms,
                             LINE_SAFETY_STATES[safety_state])

    def line_clear_safety_timer(self, line: str) -> bool:
        """
        Whisker command: clears a safety timer for a line.
        """
        return self._immbool(CMD_LINE_CLEAR_SAFETY_TIMER, line)

    # -------------------------------------------------------------------------
    # Whisker command set: audio
    # -------------------------------------------------------------------------

    def audio_play_wav(self, device: str, filename: str) -> bool:
        """
        Whisker command: play a WAV file on an audio device.

        Args:
            device: audio device number/name
            filename: WAV filename on the server

        Returns:
            success?

        """
        return self._immbool(CMD_AUDIO_PLAY_FILE, device, quote(filename))

    def audio_load_tone(self, device: str, buffer_: str,
                        frequency_hz: int, tone_type: ToneType,
                        duration_ms: int) -> bool:
        """
        Whisker command: synthesize a tone ready to be played.

        Args:
            device: audio device number/name
            buffer_: buffer name
            frequency_hz: frequency (Hz)
            tone_type: tone type (e.g. sine, square, ...)
            duration_ms: duration (ms)

        Returns:
            success?

        """
        assert isinstance(tone_type, ToneType)
        return self._immbool(
            CMD_AUDIO_LOAD_TONE,
            device,
            buffer_,
            frequency_hz,
            AUDIO_TONE_TYPES[tone_type],
            duration_ms
        )

    def audio_load_wav(self, device: str, sound: str, filename: str) -> bool:
        """
        Whisker command: load a WAV file, ready for playing.

        Args:
            device: audio device number/name
            sound: sound buffer name to create
            filename: WAV filename on the server

        Returns:
            success?

        """
        return self._immbool(CMD_AUDIO_LOAD_SOUND, device, sound,
                             quote(filename))

    def audio_play_sound(self, device: str, sound: str,
                         loop: bool = False) -> bool:
        """
        Whisker command: play a sound from a named buffer.

        Args:
            device: audio device number/name
            sound: sound buffer name to play
            loop: play it on loop?

        Returns:
            success?

        """
        args = [CMD_AUDIO_PLAY_SOUND, device, sound]
        if loop:
            args.append(FLAG_LOOP)
        return self._immbool(*args)

    def audio_unload_sound(self, device: str, sound: str) -> bool:
        """
        Whisker command: unload a sound from an audio device.

        Args:
            device: audio device number/name
            sound: sound buffer name to unload

        Returns:
            success?

        """
        return self._immbool(CMD_AUDIO_UNLOAD_SOUND, device, sound)

    def audio_stop_sound(self, device: str, sound: str) -> bool:
        """
        Whisker command: stop playing a sound.

        Args:
            device: audio device number/name
            sound: sound buffer name to stop

        Returns:
            success?

        """
        return self._immbool(CMD_AUDIO_STOP_SOUND, device, sound)

    def audio_silence_device(self, device: str) -> bool:
        """
        Whisker command: silence an audio device.
        """
        return self._immbool(CMD_AUDIO_SILENCE_DEVICE, device)

    def audio_unload_all(self, device: str) -> bool:
        """
        Whisker command: unload all sounds from an audio device.
        """
        return self._immbool(CMD_AUDIO_UNLOAD_ALL, device)

    def audio_set_sound_volume(self, device: str, sound: str,
                               volume: int) -> bool:
        """
        Whisker command: set the volume for a sound.

        Args:
            device: audio device number/name
            sound: sound buffer name to alter
            volume: from ``0`` (100 dB attentuation) to ``100`` (full volume)

        Returns:
            success

        """
        return self._immbool(CMD_AUDIO_SET_SOUND_VOLUME, device, sound, volume)

    def audio_silence_all_devices(self) -> bool:
        """
        Whisker comand: silence all audio devices.
        """
        return self._immbool(CMD_AUDIO_SILENCE_ALL_DEVICES)

    def audio_get_sound_duration_ms(self, device: str,
                                    sound: str) -> Optional[int]:
        """
        Whisker command: get the duration of a loaded sound.

        Args:
            device: audio device number/name
            sound: sound buffer name

        Returns:
            duration in ms, or ``None`` upon failure

        """
        reply = self._immresp(CMD_AUDIO_GET_SOUND_LENGTH, device, sound)
        try:
            return int(reply)
        except (TypeError, ValueError):
            return None

    # -------------------------------------------------------------------------
    # Whisker command set: display: display operations
    # -------------------------------------------------------------------------

    def display_get_size(self, device: str) -> Optional[SizeType]:
        """
        Whisker command: get the size of a display device.

        Args:
            device: display device number/name

        Returns:
            tuple: ``(width, height)`` in pixels, or ``None``

        """
        reply = self._immresp(CMD_DISPLAY_GET_SIZE, device)
        try:
            (prefix, width_str, height_str) = reply.split()
            assert prefix == MSG_SIZE
            width = int(width_str)
            height = int(height_str)
            return width, height
        except (AttributeError, TypeError, ValueError, AssertionError):
            return None

    def display_scale_documents(self, device: str, scale: bool = True) -> bool:
        """
        Whisker command: set document scaling for a display device.
        """
        return self._immbool(CMD_DISPLAY_SCALE_DOCUMENTS, device,
                             _on_val(scale))

    def display_show_document(self, device: str, doc: str) -> bool:
        """
        Whisker command: show a document on a display device.
        """
        return self._immbool(CMD_DISPLAY_SHOW_DOCUMENT, device, doc)

    def display_blank(self, device: str) -> bool:
        """
        Whisker command: blank a display device (remove any document).
        """
        return self._immbool(CMD_DISPLAY_BLANK, device)

    # -------------------------------------------------------------------------
    # Whisker command set: display: document operations
    # -------------------------------------------------------------------------

    def display_create_document(self, doc: str) -> bool:
        """
        Whisker command: create a display document.
        """
        return self._immbool(CMD_DISPLAY_CREATE_DOCUMENT, doc)

    def display_delete_document(self, doc: str) -> bool:
        """
        Whisker command: delete a display document.
        """
        return self._immbool(CMD_DISPLAY_DELETE_DOCUMENT, doc)

    def display_set_document_size(self, doc: str,
                                  width: int, height: int) -> bool:
        """
        Whisker command: set the logical size in pixels of a display document.
        """
        return self._immbool(CMD_DISPLAY_SET_DOCUMENT_SIZE, doc, width, height)

    def display_set_background_colour(self, doc: str,
                                      colour: ColourType = BLACK) -> bool:
        """
        Whisker command: set the background colour of a display document.
        """
        return self._immbool(CMD_DISPLAY_SET_BACKGROUND_COLOUR, doc,
                             colour[0], colour[1], colour[2])

    def display_delete_obj(self, doc: str, obj: str) -> bool:
        """
        Whisker command: delete a display object from a document.
        """
        return self._immbool(CMD_DISPLAY_DELETE_OBJECT, doc, obj)

    def display_add_obj(self, doc: str, obj: str, obj_type: str,
                        *parameters) -> bool:
        """
        Whisker command: add a display object to a document.

        This command has more specialized and helpful versions; don't use it
        directly.
        """
        return self._immbool(CMD_DISPLAY_ADD_OBJECT, doc, obj, obj_type,
                             *parameters)

    def display_set_event(
            self, doc: str, obj: str, event: str,
            event_type: DocEventType = DocEventType.touch_down) -> bool:
        """
        Whisker command: sets an event (e.g. responding to touchscreen or
        mouse events) on a display object within a document.

        Args:
            doc: document name
            obj: object name
            event: event to set
            event_type: event type (e.g. touched, released, mouse click, ...)

        Returns:
            success?

        """
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_SET_EVENT, doc, obj,
                             DOC_EVENT_TYPES[event_type], quote(event))

    def display_clear_event(
            self, doc: str, obj: str,
            event_type: DocEventType = DocEventType.touch_down) -> bool:
        """
        Whisker command: clears an event from a display object.

        Args:
            doc: document name
            obj: object name
            event_type: event type (e.g. touched, released, mouse click, ...)

        Returns:
            success?

        """
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_CLEAR_EVENT, doc, obj,
                             DOC_EVENT_TYPES[event_type])

    def display_set_obj_event_transparency(self, doc: str, obj: str,
                                           transparent: bool = False) -> bool:
        """
        Whisker command: set object event transparency. Transparency means:
        an object might respond (or not) to an event, but will it also let
        objects behind it respond too?

        Args:
            doc: document name
            obj: object name
            transparent: transparent?

        Returns:
            success?

        """
        return self._immbool(CMD_DISPLAY_SET_OBJ_EVENT_TRANSPARENCY,
                             doc, obj, _on_val(transparent))

    def display_event_coords(self, on: bool) -> bool:
        """
        Whisker command: enable/disable ``x``/``y`` coordinates being sent
        with relevant touchscreen/mouse events.
        """
        return self._immbool(CMD_DISPLAY_EVENT_COORDS, _on_val(on))

    def display_bring_to_front(self, doc: str, obj: str) -> bool:
        """
        Whisker command: bring an object to the front of its document (so
        it appears in front of, or on top of, other objects).
        """
        return self._immbool(CMD_DISPLAY_BRING_TO_FRONT, doc, obj)

    def display_send_to_back(self, doc: str, obj: str) -> bool:
        """
        Whisker command: send an object to the back of its document (so
        it appears behind, or underneath, other objects).
        """
        return self._immbool(CMD_DISPLAY_SEND_TO_BACK, doc, obj)

    def display_keyboard_events(
            self, doc: str,
            key_event_type: KeyEventType = KeyEventType.down) -> bool:
        """
        Whisker command: enable/disable keyboard events.

        Args:
            doc: display document
            key_event_type: choose "key down" (pressed), "key up" (released),
                both, or no events.

        Returns:
            success?

        """
        assert isinstance(key_event_type, KeyEventType)
        return self._immbool(CMD_DISPLAY_KEYBOARD_EVENTS, doc,
                             KEY_EVENT_TYPES[key_event_type])

    def display_cache_changes(self, doc: str) -> bool:
        """
        Whisker command: start caching changes to a document (to reduce
        flicker). When you've made all the changes, call
        :func:`display_show_changes`.
        """
        return self._immbool(CMD_DISPLAY_CACHE_CHANGES, doc)

    def display_show_changes(self, doc: str) -> bool:
        """
        Whisker command: show any pending changes (see
        :func:`display_cache_changes`).
        """
        return self._immbool(CMD_DISPLAY_SHOW_CHANGES, doc)

    @contextmanager
    def display_cache_wrapper(self, doc: str) -> Generator[None, None, None]:
        """
        Context manager to wrap display calls in a "cache changes",
        [do stuff], "show changes" sequence.

        Use like:

        .. code-block:: python

            with something.display_cache_wrapper(doc):
                # do some display-related things
        """
        self.display_cache_changes(doc)
        yield
        self.display_show_changes(doc)

    def display_get_document_size(self, doc: str) -> Optional[SizeType]:
        """
        Whisker command: get the logical size of a display document.

        Returns a ``(width, height)`` tuple in pixels, or ``None``.
        """
        reply = self._immresp(CMD_DISPLAY_GET_DOCUMENT_SIZE, doc)
        try:
            (prefix, width_str, height_str) = reply.split()
            assert prefix == MSG_SIZE
            width = int(width_str)
            height = int(height_str)
            return width, height
        except (AttributeError, TypeError, ValueError, AssertionError):
            return None

    def display_get_object_extent(self, doc: str,
                                  obj: str) -> Optional[Rectangle]:
        """
        Whisker command: get the rectangle describing the extend of a display
        object (in logical coordinates).

        Returns a :class:`Rectangle`, or ``None``.
        """
        reply = self._immresp(CMD_DISPLAY_GET_OBJECT_EXTENT, doc, obj)
        try:
            (prefix, left_str, top_str, right_str, bottom_str) = reply.split()
            assert prefix == MSG_EXTENT
            rect = Rectangle(
                left=int(left_str),
                right=int(right_str),
                top=int(top_str),
                bottom=int(bottom_str),
            )
            return rect
        except (AttributeError, TypeError, ValueError, AssertionError):
            return None

    def display_set_background_event(
            self, doc: str, event: str,
            event_type: DocEventType = DocEventType.touch_down) -> bool:
        """
        Whisker command: set an event for when the background of a document
        if douched (or released).

        Args:
            doc: document name
            event: event name to create
            event_type: touched, touch released, mouse click, etc.

        Returns:
            success?

        """
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_SET_BACKGROUND_EVENT, doc,
                             DOC_EVENT_TYPES[event_type], quote(event))

    def display_clear_background_event(
            self, doc: str,
            event_type: DocEventType = DocEventType.touch_down) -> bool:
        """
        Clears a document event
        
        Args:
            doc: document name
            event_type: touched, touch released, mouse click, etc.

        Returns:
            success?

        """
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_CLEAR_BACKGROUND_EVENT, doc,
                             DOC_EVENT_TYPES[event_type])

    # -------------------------------------------------------------------------
    # Whisker command set: display: specific object creation
    # -------------------------------------------------------------------------

    def display_add_obj_text(
            self,
            doc: str,
            obj: str,
            pos: PointType,
            text: str,
            height: int = 0,
            font: str = "",
            italic: bool = False,
            underline: bool = False,
            weight: int = 0,
            colour: ColourType = WHITE,
            opaque: bool = False,
            bg_colour: ColourType = BLACK,
            valign: TextVerticalAlign = TextVerticalAlign.top,
            halign: TextHorizontalAlign = TextHorizontalAlign.left) -> bool:
        """
        Whisker command: adds a Text display object.
        See Whisker help for details.
        """
        assert_ducktype_pos(pos)
        assert_ducktype_colour(colour)
        assert_ducktype_colour(bg_colour)
        assert isinstance(valign, TextVerticalAlign)
        assert isinstance(halign, TextHorizontalAlign)
        if font:
            fontargs = [FLAG_FONT, quote(font)]
        else:
            fontargs = []
        args = [
            pos[0], pos[1],
            quote(text),
            FLAG_HEIGHT, height,
            FLAG_TEXT_WEIGHT, weight,
            FLAG_TEXT_ITALIC if italic else "",
            FLAG_TEXT_UNDERLINE if underline else "",
            FLAG_TEXT_OPAQUE if opaque else "",
            FLAG_TEXT_COLOUR, colour[0], colour[1], colour[2],
            FLAG_BACKCOLOUR, bg_colour[0], bg_colour[1], bg_colour[2],
            TEXT_HALIGN_FLAGS[halign],
            TEXT_VALIGN_FLAGS[valign],
        ] + fontargs
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_TEXT, *args)

    def display_add_obj_bitmap(
            self,
            doc: str,
            obj: str,
            pos: PointType,
            filename: str,
            stretch: bool = False,
            height: int = -1,
            width: int = -1,
            valign: VerticalAlign = VerticalAlign.top,
            halign: HorizontalAlign = HorizontalAlign.left) -> bool:
        """
        Whisker command: adds a Bitmap display object.
        See Whisker help for details.
        """
        assert_ducktype_pos(pos)
        assert isinstance(valign, VerticalAlign)
        assert isinstance(halign, HorizontalAlign)
        args = [
            pos[0], pos[1],
            quote(filename),
            FLAG_BITMAP_STRETCH if stretch else FLAG_BITMAP_CLIP,
            FLAG_HEIGHT, height,
            FLAG_WIDTH, width,
            HALIGN_FLAGS[halign],
            VALIGN_FLAGS[valign],
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_BITMAP, *args)

    def display_add_obj_line(self,
                             doc: str,
                             obj: str,
                             start: PointType,
                             end: PointType,
                             pen: Pen) -> bool:
        """
        Whisker command: adds a Line display object.
        See Whisker help for details.
        """
        assert_ducktype_pos(start)
        assert_ducktype_pos(end)
        assert isinstance(pen, Pen)
        args = [
            start[0], start[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_LINE, *args)

    def display_add_obj_arc(self,
                            doc: str,
                            obj: str,
                            rect: Rectangle,
                            start, end, pen) -> bool:
        """
        Whisker command: adds an Arc display object.
        See Whisker help for details.
        
        The arc fits into the ``rect``.
        """
        assert isinstance(rect, Rectangle)
        assert_ducktype_pos(start)
        assert_ducktype_pos(end)
        assert isinstance(pen, Pen)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            start[0], start[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ARC, *args)

    def display_add_obj_bezier(self,
                               doc: str,
                               obj: str,
                               start: PointType,
                               control1: PointType,
                               control2: PointType,
                               end: PointType,
                               pen: Pen) -> bool:
        """
        Whisker command: adds a Bezier display object.
        See Whisker help for details.
        """
        assert_ducktype_pos(start)
        assert_ducktype_pos(control1)
        assert_ducktype_pos(control2)
        assert_ducktype_pos(end)
        assert isinstance(pen, Pen)
        """The control points 'pull' the curve."""
        args = [
            start[0], start[1],
            control1[0], control1[1],
            control2[0], control2[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_BEZIER, *args)

    def display_add_obj_chord(self,
                              doc: str,
                              obj: str,
                              rect: Rectangle,
                              line_start: PointType,
                              line_end: PointType,
                              pen: Pen,
                              brush: Brush) -> bool:
        """
        Whisker command: adds a Text display object.
        See Whisker help for details.
        
        The chord is the intersection of an ellipse (defined by the rect)
        and a line that intersects it.
        """
        assert isinstance(rect, Rectangle)
        assert_ducktype_pos(line_start)
        assert_ducktype_pos(line_end)
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            line_start[0], line_start[1],
            line_end[0], line_end[1],
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_CHORD, *args)

    def display_add_obj_ellipse(self,
                                doc: str,
                                obj: str,
                                rect: Rectangle,
                                pen: Pen,
                                brush: Brush) -> bool:
        """
        Whisker command: adds an Ellipse display object.
        See Whisker help for details.
        
        The ellipse fits into the rectangle (and its centre is at the centre
        of the rectangle).
        """
        assert isinstance(rect, Rectangle)
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ELLIPSE, *args)

    def display_add_obj_pie(self,
                            doc: str,
                            obj: str,
                            rect: Rectangle,
                            arc_start: PointType,
                            arc_end: PointType,
                            pen: Pen,
                            brush: Brush) -> bool:
        """
        Whisker command: adds a Pie display object.
        See Whisker help for details.
        """
        assert isinstance(rect, Rectangle)
        assert_ducktype_pos(arc_start)
        assert_ducktype_pos(arc_end)
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            arc_start[0], arc_start[1],
            arc_end[0], arc_end[1],
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_PIE, *args)

    def display_add_obj_polygon(self,
                                doc: str,
                                obj: str,
                                points: List[PointType],
                                pen: Pen,
                                brush: Brush,
                                alternate: bool = False) -> bool:
        """
        Whisker command: adds a Polygon display object.
        See Whisker help for details.
        """
        assert len(points) >= 3
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [str(len(points))]  # type: List[Any]
        for point in points:
            assert_ducktype_pos(point)
            args.extend([point[0], point[1]])
        args.extend([
            FLAG_POLYGON_ALTERNATE if alternate else FLAG_POLYGON_WINDING,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ])
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_POLYGON, *args)

    def display_add_obj_rectangle(self,
                                  doc: str,
                                  obj: str,
                                  rect: Rectangle,
                                  pen: Pen,
                                  brush: Brush) -> bool:
        """
        Whisker command: adds a Rectangle display object.
        See Whisker help for details.
        """
        assert isinstance(rect, Rectangle)
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_RECTANGLE, *args)

    def display_add_obj_roundrect(self,
                                  doc: str,
                                  obj: str,
                                  rect: Rectangle,
                                  ellipse_height: int,
                                  ellipse_width: int,
                                  pen: Pen,
                                  brush: Brush) -> bool:
        """
        Whisker command: adds a RoundRect display object.
        See Whisker help for details.
        """
        assert isinstance(rect, Rectangle)
        assert isinstance(pen, Pen)
        assert isinstance(brush, Brush)
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            ellipse_width, ellipse_height,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ROUNDRECT, *args)

    def display_add_obj_camcogquadpattern(self,
                                          doc: str,
                                          obj: str,
                                          pos: PointType,
                                          pixel_width: int,
                                          pixel_height: int,
                                          top_left_patterns: List[int],
                                          top_right_patterns: List[int],
                                          bottom_left_patterns: List[int],
                                          bottom_right_patterns: List[int],
                                          top_left_colour: ColourType,
                                          top_right_colour: ColourType,
                                          bottom_left_colour: ColourType,
                                          bottom_right_colour: ColourType,
                                          bg_colour: ColourType) -> bool:
        """
        Whisker command: adds a CamcogQuadPattern display object.
        See Whisker help for details.

        Patterns are lists (of length 8) of bytes.
        """
        assert len(top_left_patterns) == 8
        assert len(top_right_patterns) == 8
        assert len(bottom_left_patterns) == 8
        assert len(bottom_right_patterns) == 8
        assert_ducktype_colour(top_left_colour)
        assert_ducktype_colour(top_right_colour)
        assert_ducktype_colour(bottom_left_colour)
        assert_ducktype_colour(bottom_right_colour)
        assert_ducktype_colour(bg_colour)
        args = [pos[0], pos[1], pixel_width, pixel_height]
        args.extend(top_left_patterns)
        args.extend(top_right_patterns)
        args.extend(bottom_left_patterns)
        args.extend(bottom_right_patterns)
        args.extend(top_left_colour)
        args.extend(top_right_colour)
        args.extend(bottom_left_colour)
        args.extend(bottom_right_colour)
        args.extend(bg_colour)
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_CAMCOGQUADPATTERN,
                                    *args)

    # -------------------------------------------------------------------------
    # Whisker command set: display: video extras
    # -------------------------------------------------------------------------

    def display_add_obj_video(self,
                              doc: str,
                              video: str,
                              pos: PointType,
                              filename: str,
                              loop: bool = False,
                              playmode: VideoPlayMode = VideoPlayMode.wait,
                              width: int = -1,
                              height: int = -1,
                              play_audio: bool = True,
                              valign: VerticalAlign = VerticalAlign.top,
                              halign: HorizontalAlign = HorizontalAlign.left,
                              bg_colour: ColourType = BLACK) -> bool:
        """
        Whisker command: adds a Video display object.
        See Whisker help (http://www.whiskercontrol.com) for details.
        """
        assert isinstance(playmode, VideoPlayMode)
        assert isinstance(valign, VerticalAlign)
        assert isinstance(halign, HorizontalAlign)
        assert_ducktype_colour(bg_colour)
        args = [
            pos[0], pos[1],
            quote(filename),
            FLAG_LOOP if loop else FLAG_VIDEO_NOLOOP,
            VIDEO_PLAYMODE_FLAGS[playmode],
            FLAG_WIDTH, width,
            FLAG_HEIGHT, height,
            FLAG_VIDEO_AUDIO if play_audio else FLAG_VIDEO_NOAUDIO,
            HALIGN_FLAGS[halign],
            VALIGN_FLAGS[valign],
            FLAG_BACKCOLOUR, bg_colour[0], bg_colour[1], bg_colour[2],
        ]
        return self.display_add_obj(doc, video, VAL_OBJTYPE_VIDEO, *args)

    def display_set_audio_device(self, display_device: str,
                                 audio_device: str) -> bool:
        """
        Whisker command: sets the audio device associated with a display
        device, for video playback.

        Args:
            display_device: display device number/name
            audio_device: audio device number/name

        Returns:
            success?

        """
        return self._immbool(CMD_DISPLAY_SET_AUDIO_DEVICE, display_device,
                             audio_device)

    def video_play(self, doc: str, video: str) -> bool:
        """
        Whisker command: plays a video.
        """
        return self._immbool(CMD_VIDEO_PLAY, doc, video)

    def video_pause(self, doc: str, video: str) -> bool:
        """
        Whisker command: pauses a video.
        """
        return self._immbool(CMD_VIDEO_PAUSE, doc, video)

    def video_stop(self, doc: str, video: str) -> bool:
        """
        Whisker command: stops a video.
        """
        return self._immbool(CMD_VIDEO_STOP, doc, video)

    def video_timestamps(self, on: bool) -> bool:
        """
        Whisker command: enables/disables the sending of video times (in ms)
        being sent along with "video touched" events.
        """
        return self._immbool(CMD_VIDEO_TIMESTAMPS, _on_val(on))

    def video_get_time_ms(self, doc: str, video: str) -> Optional[int]:
        """
        Whisker command: gets the current video time (since the start).

        Args:
            doc: display document name
            video: video name

        Returns:
            time in ms, or ``None``

        """
        reply = self._immresp(CMD_VIDEO_GET_TIME, doc, video)
        try:
            return int(reply.split()[1])
        except (IndexError, ValueError):
            return None

    def video_get_duration_ms(self, doc: str, video: str) -> Optional[int]:
        """
        Whisker command: gets a video's duration.

        Args:
            doc: display document name
            video: video name

        Returns:
            duration in ms, or ``None``

        """
        reply = self._immresp(CMD_VIDEO_GET_DURATION, doc, video)
        try:
            return int(reply.split()[1])
        except (IndexError, ValueError):
            return None

    def video_seek_relative(self, doc: str, video: str, time_ms: int) -> bool:
        """
        Whisker command: execute a "seek" command on a video, using relative
        time (e.g. +5000 ms for 5 seconds forwards; -5000 ms for 5 seconds
        backwards).
        """
        return self._immbool(CMD_VIDEO_SEEK_RELATIVE, doc, video, time_ms)

    def video_seek_absolute(self, doc: str, video: str, time_ms: int) -> bool:
        """
        Whisker command: execute a "seek" command on a video, using absolute
        time (milliseconds since the video's start).
                """
        return self._immbool(CMD_VIDEO_SEEK_ABSOLUTE, doc, video, time_ms)

    def video_set_volume(self, doc: str, video: str, volume: int) -> bool:
        """

        Args:
            doc: display document name
            video: video name
            volume: from ``0`` (minimum) to ``100`` (full)

        Returns:
            success?

        """
        return self._immbool(CMD_VIDEO_SET_VOLUME, doc, video, volume)

    # -------------------------------------------------------------------------
    # Shortcuts to Whisker commands
    # -------------------------------------------------------------------------

    def line_on(self, line: str) -> None:
        """
        Turns a line on.
        """
        self.line_set_state(line, True)

    def line_off(self, line: str) -> None:
        """
        Turns a line off.
        """
        self.line_set_state(line, False)

    def broadcast(self, *args) -> bool:
        """
        Broadcasts a message to all other clients of this Whisker server that
        are listening.
        """
        return self.send_to_client(-1, *args)
