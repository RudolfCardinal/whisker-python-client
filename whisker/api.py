#!/usr/bin/env python
# whisker/api.py

from contextlib import contextmanager
from enum import Enum, unique
import logging
import re

from whisker.callback import CallbackHandler

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
CLIENT_MESSAGE_REGEX = re.compile(r"^ClientMessage: (.*)$")
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

def _on_val(on):
    return VAL_ON if on else VAL_OFF


def split_timestamp(msg):
    try:
        m = TIMESTAMP_REGEX.match(msg)
        mainmsg = m.group(1)
        timestamp = int(m.group(2))
        return (mainmsg, timestamp)
    except:
        return (msg, None)


def on_off_to_boolean(msg):
    return True if msg == VAL_ON else False


def s_to_ms(time_seconds):
    return int(time_seconds * 1000)


def min_to_ms(time_minutes):
    return int(time_minutes * 60000)


def quote(string):
    return QUOTE + string + QUOTE  # suboptimal! Doesn't escape quotes.


def msg_from_args(*args):
    str_versions = [str(x) for x in args]
    return " ".join(x for x in str_versions if x)


class Rectangle(object):
    def __init__(self, left, top, width=None, height=None,
                 right=None, bottom=None):
        # Origin is at top left, as per Whisker.
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
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def right(self):
        return self._left + self._width

    @property
    def bottom(self):
        return self._top + self._height

    @property
    def centre_x(self):
        return self._left + self._width / 2

    @property
    def centre_y(self):
        return self._top + self._height / 2

    @property
    def centre(self):
        return (self.centre_x, self.centre_y)

    @property
    def left_top(self):
        return (self._left, self.top)

    @property
    def right_bottom(self):
        return (self._right, self.bottom)


class Pen(object):
    def __init__(self, width=1, colour=(255, 255, 255), style=PenStyle.solid):
        self.style = style
        self.width = width
        self.colour = colour

    @property
    def whisker_option_string(self):
        args = [
            FLAG_PEN_COLOUR, self.colour[0], self.colour[1], self.colour[2],
            FLAG_PEN_WIDTH, self.width,
            FLAG_PEN_STYLE, PEN_STYLE_FLAGS[self.style],
        ]
        return msg_from_args(*args)


class Brush(object):
    def __init__(self, colour=(255, 255, 255), bg_colour=(0, 0, 0),
                 opaque=True, style=BrushStyle.solid,
                 hatch_style=BrushHatchStyle.cross):
        self.colour = colour
        self.bg_colour = bg_colour
        self.opaque = opaque
        self.style = style
        self.hatch_style = hatch_style

    @property
    def whisker_option_string(self):
        args = [BRUSH_STYLE_FLAGS[self.style]]
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


def ducktype_colour(colour):
    err = "Bad colour: must be (R, G, B) tuple. Was: {}"
    if len(colour) != 3:
        raise ValueError(err.format(colour))
    (r, g, b) = colour
    if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
        return True
    raise ValueError(err.format(colour))


# =============================================================================
# API handler. Distinct from any particular network/threading
# model, so all can use it (e.g. by inheritance), but hooks in to whichever
# you choose.
# =============================================================================

class WhiskerApi(object):
    def __init__(self, whisker_immsend_get_reply_fn, sysevent_prefix="sys_"):
        """
        The function whisker_immsend_get_reply_fn must take arguments *args,
        join stringified versions of them using a space as the separator, and
        send them to the Whisker server via the immediate socket, returning the
        string that the server sent back.
        """
        self._immsend_get_reply = whisker_immsend_get_reply_fn
        self.sysevent_prefix = sysevent_prefix
        self.sysevent_counter = 0
        self.callback_handler = CallbackHandler()

    # -------------------------------------------------------------------------
    # Internal derived comms
    # -------------------------------------------------------------------------

    def _immresp(self, *args):
        reply = self._immsend_get_reply(*args)
        (reply, whisker_timestamp) = split_timestamp(reply)
        return reply

    def _immbool(self, *args):
        reply = self._immresp(*args)
        return reply == RESPONSE_SUCCESS

    # -------------------------------------------------------------------------
    # Custom event handling, e.g. for line flashing
    # -------------------------------------------------------------------------

    def get_new_sysevent(self, *args):
        self.sysevent_counter += 1
        return self.sysevent_prefix + "_".join(
            str(x) for x in [self.sysevent_counter] + list(args)
        ).replace(" ", "")

    def process_backend_event(self, event):
        """Returns True if the backend API has dealt with the event and it
        doesn't need to go to the main behavioural task."""
        n_called, swallow_event = self.callback_handler.process_event(event)
        return (
            (n_called > 0 and swallow_event) or
            event.startswith(self.sysevent_prefix)
        )

    def send_after_delay(self, delay_ms, msg, event=''):
        event = event or self.get_new_sysevent("send", msg)
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, self._immsend, msg)

    def call_after_delay(self, delay_ms, callback, args=None, kwargs=None,
                         event=''):
        args = args or []
        kwargs = kwargs or {}
        event = event or self.get_new_sysevent("call")
        self.timer_set_event(event, delay_ms)
        self.callback_handler.add_single(event, callback, args, kwargs)

    def call_on_event(self, event, callback, args=None, kwargs=None,
                      swallow_event=False):
        args = args or []
        kwargs = kwargs or {}
        self.callback_handler.add_persistent(event, callback, args, kwargs,
                                             swallow_event=swallow_event)

    def clear_event_callback(self, event, callback=None):
        self.callback_handler.remove(event, callback=callback)

    def clear_all_callbacks(self):
        self.callback_handler.clear()

    def debug_callbacks(self):
        self.callback_handler.debug()

    # -------------------------------------------------------------------------
    # Line flashing
    # -------------------------------------------------------------------------

    def flash_line_pulses(self, line, count, on_ms, off_ms, on_at_rest=False):
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

    def flash_line_ping_pong(self, line, on_now, timing_sequence):
        """
        line: line number/name
        on_now: switch it on or off now?
        timing_sequence: array of times (in ms) for the next things
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

    def timestamps(self, on):
        return self._immbool(CMD_TIMESTAMPS, _on_val(on))

    def reset_clock(self, on):
        return self._immbool(CMD_RESET_CLOCK)

    def get_server_version(self):
        return self._immresp(CMD_VERSION)

    def get_server_version_numeric(self):
        return float(self.get_server_version())

    def get_server_time_ms(self):
        return int(self._immresp(CMD_REQUEST_TIME))

    def get_client_number(self):
        return int(self._immresp(CMD_CLIENT_NUMBER))

    def permit_client_messages(self, permit):
        return self._immbool(CMD_PERMIT_CLIENT_MESSAGES, _on_val(permit))

    def send_to_client(self, client_num, msg):
        return self._immbool(CMD_SEND_TO_CLIENT, client_num, msg)

    def set_media_directory(self, directory):
        return self._immbool(CMD_SET_MEDIA_DIRECTORY, quote(directory))

    def report_name(self, name):
        return self._immbool(CMD_REPORT_NAME, quote(name))

    def report_status(self, status):
        return self._immbool(CMD_REPORT_STATUS, quote(status))

    def report_comment(self, comment):
        return self._immbool(CMD_REPORT_COMMENT, quote(comment))

    def get_network_latency_ms(self):
        reply = self._immresp(CMD_TEST_NETWORK_LATENCY)
        if reply != PING:
            return None
        try:
            reply = self._immresp(PING_ACK)
            return int(reply)
        except:
            return None

    def shutdown(self):
        return self._immbool(CMD_SHUTDOWN)

    def authenticate_get_challenge(self, package, client_name, challenge):
        reply = self._immresp(CMD_AUTHENTICATE, package, client_name)
        if not reply.startswith(MSG_AUTHENTICATE_CHALLENGE + " "):
            return None
        challenge = reply.split()[1]
        return challenge

    def authenticate_provide_response(self, response):
        return self._immbool(CMD_AUTHENTICATE_RESPONSE, response)

    # -------------------------------------------------------------------------
    # Whisker command set: logs
    # -------------------------------------------------------------------------

    def log_open(self, filename):
        return self._immbool(CMD_LOG_OPEN, quote(filename))

    def log_set_options(self, events=True, key_events=True, client_client=True,
                        comms=False, signature=True):
        return self._immbool(
            CMD_LOG_SET_OPTIONS,
            FLAG_EVENTS, _on_val(events),
            FLAG_KEYEVENTS, _on_val(key_events),
            FLAG_CLIENTCLIENT, _on_val(client_client),
            FLAG_COMMS, _on_val(comms),
            FLAG_SIGNATURE, _on_val(signature),
        )

    def log_pause(self):
        return self._immbool(CMD_LOG_PAUSE)

    def log_resume(self):
        return self._immbool(CMD_LOG_RESUME)

    def log_write(self, msg):
        return self._immbool(CMD_LOG_WRITE, msg)

    def log_close(self):
        return self._immbool(CMD_LOG_CLOSE)

    # -------------------------------------------------------------------------
    # Whisker command set: timers
    # -------------------------------------------------------------------------

    def timer_set_event(self, event, duration_ms, reload_count=0):
        return self._immbool(CMD_TIMER_SET_EVENT, duration_ms, reload_count,
                             event)

    def timer_clear_event(self, event):
        return self._immbool(CMD_TIMER_CLEAR_EVENT, event)

    def timer_clear_all_events(self):
        return self._immbool(CMD_TIMER_CLEAR_ALL_EVENTS)

    # -------------------------------------------------------------------------
    # Whisker command set: claiming, relinquishing
    # -------------------------------------------------------------------------

    def claim_group(self, group, prefix, suffix):
        args = [CMD_CLAIM_GROUP]
        if prefix:
            args += [FLAG_PREFIX, prefix]
        if suffix:
            args += [FLAG_SUFFIX, suffix]
        return self._immbool(*args)

    def claim_line(self, line, output=False, reset_state=ResetState.leave,
                   alias=""):
        assert isinstance(reset_state, ResetState)
        if not output:
            reset_state = ResetState.input
        args = [CMD_LINE_CLAIM,
                FLAG_OUTPUT if output else FLAG_INPUT,
                LINE_RESET_FLAGS[reset_state]]
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def relinquish_all_lines(self):
        return self._immbool(CMD_LINE_RELINQUISH_ALL)

    def line_set_alias(self, line, alias):
        return self._immbool(CMD_LINE_SET_ALIAS, line, alias)

    def claim_audio_by_num(self, device_num, alias=""):
        args = [CMD_AUDIO_CLAIM, device_num]
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def claim_audio_by_name(self, device_group, device_name, alias=""):
        args = [CMD_AUDIO_CLAIM, device_group, device_name]
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def audio_set_alias(self, from_, to):
        return self._immbool(CMD_AUDIO_SET_ALIAS, from_, to)

    def relinquish_all_audio(self):
        return self._immbool(CMD_AUDIO_RELINQUISH_ALL)

    def claim_display_by_name(self, group, device, alias=""):
        # Autocreating debug views not supported (see C++ WhiskerClientLib).
        args = [CMD_DISPLAY_CLAIM, group, device]
        if alias:
            args.extend([FLAG_ALIAS, alias])
        return self._immbool(*args)

    def claim_display_by_num(self, device_num, alias=""):
        # Autocreating debug views not supported (see C++ WhiskerClientLib).
        return self.claim_display_by_name(str(device_num), "", alias=alias)

    def display_set_alias(self, from_, to):
        return self._immbool(CMD_DISPLAY_SET_ALIAS, from_, to)

    def relinquish_all_displays(self):
        return self._immbool(CMD_DISPLAY_RELINQUISH_ALL)

    def display_create_device(self, name, resize=True, directdraw=True,
                              rectangle=None, debug_touches=False):
        args = [
            CMD_DISPLAY_CREATE_DEVICE,
            name,
            FLAG_RESIZE, _on_val(resize),
            FLAG_DIRECTDRAW, _on_val(directdraw),
        ]
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

    def display_delete_device(self, device):
        return self._immbool(CMD_DISPLAY_DELETE_DEVICE, device)

    # -------------------------------------------------------------------------
    # Whisker command set: lines
    # -------------------------------------------------------------------------

    def line_set_state(self, line, on):
        return self._immbool(CMD_LINE_SET_STATE, line, _on_val(on))

    def line_read_state(self, line):
        """Returns a boolean representing the line state, or None upon
        failure."""
        reply = self._immresp(CMD_LINE_READ_STATE, line)
        if reply == VAL_ON:
            return True
        elif reply == VAL_OFF:
            return False
        else:
            return None

    def line_set_event(self, line, event, event_type=LineEventType.on):
        assert isinstance(event_type, LineEventType)
        return self._immbool(CMD_LINE_SET_EVENT, line,
                             LINE_EVENT_TYPES[event_type], event)

    def line_clear_event(self, event):
        return self._immbool(CMD_LINE_CLEAR_EVENT, event)

    def line_clear_event_by_line(self, line, event_type):
        assert isinstance(event_type, LineEventType)
        return self._immbool(CMD_LINE_CLEAR_EVENTS_BY_LINE, line,
                             LINE_EVENT_TYPES[event_type])

    def line_clear_all_events(self):
        return self._immbool(CMD_LINE_CLEAR_ALL_EVENTS)

    def line_set_safety_timer(self, line, time_ms, safety_state):
        assert isinstance(safety_state, SafetyState)
        return self._immbool(CMD_LINE_SET_SAFETY_TIMER, line, time_ms,
                             LINE_SAFETY_STATES[safety_state])

    def line_clear_safety_timer(self, line):
        return self._immbool(CMD_LINE_CLEAR_SAFETY_TIMER, line)

    # -------------------------------------------------------------------------
    # Whisker command set: audio
    # -------------------------------------------------------------------------

    def audio_play_wav(self, device, filename):
        return self._immbool(CMD_AUDIO_PLAY_FILE, device, quote(filename))

    def audio_load_tone(self, device, buffer_, frequency_hz, tone_type,
                        duration_ms):
        assert isinstance(tone_type, ToneType)
        return self._immbool(
            CMD_AUDIO_LOAD_TONE,
            device,
            buffer_,
            frequency_hz,
            AUDIO_TONE_TYPES[tone_type],
            duration_ms
        )

    def audio_load_wav(self, device, sound, filename):
        return self._immbool(CMD_AUDIO_LOAD_SOUND, device, sound,
                             quote(filename))

    def audio_play_sound(self, device, sound, loop=False):
        args = [CMD_AUDIO_PLAY_SOUND, device, sound]
        if loop:
            args.append(FLAG_LOOP)
        return self._immbool(*args)

    def audio_unload_sound(self, device, sound):
        return self._immbool(CMD_AUDIO_UNLOAD_SOUND, device, sound)

    def audio_stop_sound(self, device, sound):
        return self._immbool(CMD_AUDIO_STOP_SOUND, device, sound)

    def audio_silence_device(self, device):
        return self._immbool(CMD_AUDIO_SILENCE_DEVICE, device)

    def audio_unload_all(self, device):
        return self._immbool(CMD_AUDIO_UNLOAD_ALL, device)

    def audio_set_sound_volume(self, device, sound, volume):
        return self._immbool(CMD_AUDIO_SET_SOUND_VOLUME, device, sound, volume)

    def audio_silence_all_devices(self):
        return self._immbool(CMD_AUDIO_SILENCE_ALL_DEVICES)

    def audio_get_sound_duration_ms(self, device, sound):
        reply = self._immresp(CMD_AUDIO_GET_SOUND_LENGTH, device, sound)
        try:
            return int(reply)
        except:
            return None

    # -------------------------------------------------------------------------
    # Whisker command set: display: display operations
    # -------------------------------------------------------------------------

    def display_get_size(self, device):
        """Returns a (width, height) tuple, or None."""
        reply = self._immresp(CMD_DISPLAY_GET_SIZE, device)
        try:
            (prefix, width_str, height_str) = reply.split()
            assert prefix == MSG_SIZE
            width = int(width_str)
            height = int(height_str)
            return (width, height)
        except:
            return None

    def display_scale_documents(self, device, scale=True):
        return self._immbool(CMD_DISPLAY_SCALE_DOCUMENTS, _on_val(scale))

    def display_show_document(self, device, doc):
        return self._immbool(CMD_DISPLAY_SHOW_DOCUMENT, device, doc)

    def display_blank(self, device):
        return self._immbool(CMD_DISPLAY_BLANK, device)

    # -------------------------------------------------------------------------
    # Whisker command set: display: document operations
    # -------------------------------------------------------------------------

    def display_create_document(self, doc):
        return self._immbool(CMD_DISPLAY_CREATE_DOCUMENT, doc)

    def display_delete_document(self, doc):
        return self._immbool(CMD_DISPLAY_DELETE_DOCUMENT, doc)

    def display_set_document_size(self, doc, width, height):
        return self._immbool(CMD_DISPLAY_SET_DOCUMENT_SIZE, doc, width, height)

    def display_set_background_colour(self, doc, colour=(0, 0, 0)):
        return self._immbool(CMD_DISPLAY_SET_BACKGROUND_COLOUR, doc,
                             colour[0], colour[1], colour[2])

    def display_delete_obj(self, doc, obj):
        return self._immbool(CMD_DISPLAY_DELETE_OBJECT, doc, obj)

    def display_add_obj(self, doc, obj, obj_type, *parameters):
        return self._immbool(CMD_DISPLAY_ADD_OBJECT, doc, obj, obj_type,
                             *parameters)

    def display_set_event(self, doc, obj, event,
                          event_type=DocEventType.touch_down):
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_SET_EVENT, doc, obj,
                             DOC_EVENT_TYPES[event_type], quote(event))

    def display_clear_event(self, doc, obj,
                            event_type=DocEventType.touch_down):
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_CLEAR_EVENT, doc, obj,
                             DOC_EVENT_TYPES[event_type])

    def display_set_obj_event_transparency(self, doc, obj, transparent=False):
        return self._immbool(CMD_DISPLAY_SET_OBJ_EVENT_TRANSPARENCY,
                             doc, obj, _on_val(transparent))

    def display_event_coords(self, on):
        return self._immbool(CMD_DISPLAY_EVENT_COORDS, _on_val(on))

    def display_bring_to_front(self, doc, obj):
        return self._immbool(CMD_DISPLAY_BRING_TO_FRONT, doc, obj)

    def display_send_to_back(self, doc, obj):
        return self._immbool(CMD_DISPLAY_SEND_TO_BACK, doc, obj)

    def display_keyboard_events(self, doc, key_event_type=KeyEventType.down):
        assert isinstance(key_event_type, KeyEventType)
        return self._immbool(CMD_DISPLAY_KEYBOARD_EVENTS, doc,
                             KEY_EVENT_TYPES[key_event_type])

    def display_cache_changes(self, doc):
        return self._immbool(CMD_DISPLAY_CACHE_CHANGES, doc)

    def display_show_changes(self, doc):
        return self._immbool(CMD_DISPLAY_SHOW_CHANGES, doc)

    @contextmanager
    def display_cache_wrapper(self, doc):
        """
        Use like:
            with something.display_cache_wrapper(doc):
                # do some display-related things
        """
        self.display_cache_changes(doc)
        yield
        self.display_show_changes(doc)

    def display_get_document_size(self, doc):
        """Returns a (width, height) tuple, or None."""
        reply = self._immresp(CMD_DISPLAY_GET_DOCUMENT_SIZE, doc)
        try:
            (prefix, width_str, height_str) = reply.split()
            assert prefix == MSG_SIZE
            width = int(width_str)
            height = int(height_str)
            return (width, height)
        except:
            return None

    def display_get_object_extent(self, doc, obj):
        """Returns a rect, or None."""
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
        except:
            return None

    def display_set_background_event(self, doc, event,
                                     event_type=DocEventType.touch_down):
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_SET_BACKGROUND_EVENT, doc,
                             DOC_EVENT_TYPES[event_type], quote(event))

    def display_clear_background_event(self, doc, event,
                                       event_type=DocEventType.touch_down):
        assert isinstance(event_type, DocEventType)
        return self._immbool(CMD_DISPLAY_CLEAR_BACKGROUND_EVENT, doc,
                             DOC_EVENT_TYPES[event_type])

    # -------------------------------------------------------------------------
    # Whisker command set: display: specific object creation
    # -------------------------------------------------------------------------

    def display_add_obj_text(self, doc, obj, pos, text, height=0, font="",
                             italic=False, underline=False, weight=0,
                             colour=(255, 255, 255), opaque=False,
                             bg_colour=(0, 0, 0),
                             valign=TextVerticalAlign.top,
                             halign=TextHorizontalAlign.left):
        """Position is an (x, y) tuple. Colours are R, G, B tuples."""
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

    def display_add_obj_bitmap(self, doc, obj, pos, filename,
                               stretch=False, height=-1, width=-1,
                               valign=VerticalAlign.top,
                               halign=HorizontalAlign.left):
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

    def display_add_obj_line(self, doc, obj, start, end, pen):
        """Coordinates are (x, y) tuples."""
        args = [
            start[0], start[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_LINE, *args)

    def display_add_obj_arc(self, doc, obj, rect, start, end, pen):
        """The arc fits into the rect."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            start[0], start[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ARC, *args)

    def display_add_obj_bezier(self, doc, obj, start, control1, control2, end,
                               pen):
        """The control points 'pull' the curve."""
        args = [
            start[0], start[1],
            control1[0], control1[1],
            control2[0], control2[1],
            end[0], end[1],
            pen.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_BEZIER, *args)

    def display_add_obj_chord(self, doc, obj, rect, line_start, line_end,
                              pen, brush):
        """The chord is the intersection of an ellipse (defined by the rect)
        and a line that intersects it."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            line_start[0], line_start[1],
            line_end[0], line_end[1],
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_CHORD, *args)

    def display_add_obj_ellipse(self, doc, obj, rect, pen, brush):
        """The ellipse fits into the rectangle (and its centre is at the centre
        of the rectangle)."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ELLIPSE, *args)

    def display_add_obj_pie(self, doc, obj, rect, arc_start, arc_end,
                            pen, brush):
        """See Whisker docs."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            arc_start[0], arc_start[1],
            arc_end[0], arc_end[1],
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_PIE, *args)

    def display_add_obj_polygon(self, doc, obj, points, pen, brush,
                                alternate=False):
        """See Whisker docs."""
        args = [len(points)]
        for point in points:
            args.extend([point[0], point[1]])
        args.extend([
            FLAG_POLYGON_ALTERNATE if alternate else FLAG_POLYGON_WINDING,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ])
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_POLYGON, *args)

    def display_add_obj_rectangle(self, doc, obj, rect, pen, brush):
        """See Whisker docs."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_RECTANGLE, *args)

    def display_add_obj_roundrect(self, doc, obj, rect, ellipse_height,
                                  ellipse_width, pen, brush):
        """See Whisker docs."""
        args = [
            rect.left, rect.top,
            rect.right, rect.bottom,
            ellipse_width, ellipse_height,
            pen.whisker_option_string,
            brush.whisker_option_string,
        ]
        return self.display_add_obj(doc, obj, VAL_OBJTYPE_ROUNDRECT, *args)

    def display_add_obj_camcogquadpattern(
            self, doc, obj, pos,
            pixel_width, pixel_height,
            top_left_patterns, top_right_patterns,
            bottom_left_patterns, bottom_right_patterns,
            top_left_colour, top_right_colour,
            bottom_left_colour, bottom_right_colour,
            bg_colour):
        """
        See Whisker docs.
        Patterns are lists (of length 8) of bytes.
        Colours are R, G, B tuples.
        """
        assert len(top_left_patterns) == 8
        assert len(top_right_patterns) == 8
        assert len(bottom_left_patterns) == 8
        assert len(bottom_right_patterns) == 8
        assert ducktype_colour(top_left_colour)
        assert ducktype_colour(top_right_colour)
        assert ducktype_colour(bottom_left_colour)
        assert ducktype_colour(bottom_right_colour)
        assert ducktype_colour(bg_colour)
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

    def display_add_obj_video(self, doc, video, x, y, filename, loop=False,
                              playmode=VideoPlayMode.wait, width=-1, height=-1,
                              play_audio=True, valign=VerticalAlign.top,
                              halign=HorizontalAlign.left,
                              bg_colour=(0, 0, 0)):
        args = [
            x, y,
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

    def display_set_audio_device(self, display_device, audio_device):
        """Devices may be specified as numbers or names."""
        return self._immbool(CMD_DISPLAY_SET_AUDIO_DEVICE, display_device,
                             audio_device)

    def video_play(self, doc, video):
        return self._immbool(CMD_VIDEO_PLAY, doc, video)

    def video_pause(self, doc, video):
        return self._immbool(CMD_VIDEO_PAUSE, doc, video)

    def video_stop(self, doc, video):
        return self._immbool(CMD_VIDEO_STOP, doc, video)

    def video_timestamps(self, on):
        return self._immbool(CMD_VIDEO_TIMESTAMPS, _on_val(on))

    def video_get_time_ms(self, doc, video):
        reply = self._immresp(CMD_VIDEO_GET_TIME, doc, video)
        try:
            return int(reply.split()[1])
        except (IndexError, ValueError):
            return None

    def video_get_duration_ms(self, doc, video):
        reply = self._immresp(CMD_VIDEO_GET_DURATION, doc, video)
        try:
            return int(reply.split()[1])
        except (IndexError, ValueError):
            return None

    def video_seek_relative(self, doc, video, time_ms):
        return self._immbool(CMD_VIDEO_SEEK_RELATIVE, doc, video, time_ms)

    def video_seek_absolute(self, doc, video, time_ms):
        return self._immbool(CMD_VIDEO_SEEK_ABSOLUTE, doc, video, time_ms)

    def video_set_volume(self, doc, video, volume):
        return self._immbool(CMD_VIDEO_SET_VOLUME, doc, video, volume)

    # -------------------------------------------------------------------------
    # Shortcuts to Whisker commands
    # -------------------------------------------------------------------------

    def line_on(self, line):
        self.line_set_state(line, True)

    def line_off(self, line):
        self.line_set_state(line, False)
