import _v8
from .utils import is_py3k

try:
    import json
except ImportError:
    import simplejson as json

if is_py3k:
    import _thread as thread
    from io import StringIO
    unicode = str
else:
    import thread

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

class JSDebugProtocol(object):
    """
    Support the V8 debugger JSON based protocol.

    <http://code.google.com/p/v8/wiki/DebuggerProtocol>
    """
    class Packet(object):
        REQUEST = 'request'
        RESPONSE = 'response'
        EVENT = 'event'

        def __init__(self, payload):
            self.data = json.loads(payload) if type(payload) in [str, unicode] else payload

        @property
        def seq(self):
            return self.data['seq']

        @property
        def type(self):
            return self.data['type']

    class Request(Packet):
        @property
        def cmd(self):
            return self.data['command']

        @property
        def args(self):
            return self.data['args']

    class Response(Packet):
        @property
        def request_seq(self):
            return self.data['request_seq']

        @property
        def cmd(self):
            return self.data['command']

        @property
        def body(self):
            return self.data['body']

        @property
        def running(self):
            return self.data['running']

        @property
        def success(self):
            return self.data['success']

        @property
        def message(self):
            return self.data['message']

    class Event(Packet):
        @property
        def event(self):
            return self.data['event']

        @property
        def body(self):
            return self.data['body']

    def __init__(self):
        self.seq = 0

    def nextSeq(self):
        seq = self.seq
        self.seq += 1

        return seq

    def parsePacket(self, payload):
        obj = json.loads(payload)

        return JSDebugProtocol.Event(obj) if obj['type'] == 'event' else JSDebugProtocol.Response(obj)


class JSDebugEvent(_v8.JSDebugEvent):
    class FrameData(object):
        def __init__(self, frame, count, name, value):
            self.frame = frame
            self.count = count
            self.name = name
            self.value = value

        def __len__(self):
            return self.count(self.frame)

        def __iter__(self):
            for i in range(self.count(self.frame)):
                yield (self.name(self.frame, i), self.value(self.frame, i))

    class Frame(object):
        def __init__(self, frame):
            self.frame = frame

        @property
        def index(self):
            return int(self.frame.index())

        @property
        def function(self):
            return self.frame.func()

        @property
        def receiver(self):
            return self.frame.receiver()

        @property
        def isConstructCall(self):
            return bool(self.frame.isConstructCall())

        @property
        def isDebuggerFrame(self):
            return bool(self.frame.isDebuggerFrame())

        @property
        def argumentCount(self):
            return int(self.frame.argumentCount())

        def argumentName(self, idx):
            return str(self.frame.argumentName(idx))

        def argumentValue(self, idx):
            return self.frame.argumentValue(idx)

        @property
        def arguments(self):
            return JSDebugEvent.FrameData(self, self.argumentCount, self.argumentName, self.argumentValue)

        def localCount(self, idx):
            return int(self.frame.localCount())

        def localName(self, idx):
            return str(self.frame.localName(idx))

        def localValue(self, idx):
            return self.frame.localValue(idx)

        @property
        def locals(self):
            return JSDebugEvent.FrameData(self, self.localCount, self.localName, self.localValue)

        @property
        def sourcePosition(self):
            return self.frame.sourcePosition()

        @property
        def sourceLine(self):
            return int(self.frame.sourceLine())

        @property
        def sourceColumn(self):
            return int(self.frame.sourceColumn())

        @property
        def sourceLineText(self):
            return str(self.frame.sourceLineText())

        def evaluate(self, source, disable_break = True):
            return self.frame.evaluate(source, disable_break)

        @property
        def invocationText(self):
            return str(self.frame.invocationText())

        @property
        def sourceAndPositionText(self):
            return str(self.frame.sourceAndPositionText())

        @property
        def localsText(self):
            return str(self.frame.localsText())

        def __str__(self):
            return str(self.frame.toText())

    class Frames(object):
        def __init__(self, state):
            self.state = state

        def __len__(self):
            return self.state.frameCount

        def __iter__(self):
            for i in range(self.state.frameCount):
                yield self.state.frame(i)

    class State(object):
        def __init__(self, state):
            self.state = state

        @property
        def frameCount(self):
            return int(self.state.frameCount())

        def frame(self, idx = None):
            return JSDebugEvent.Frame(self.state.frame(idx))

        @property
        def selectedFrame(self):
            return int(self.state.selectedFrame())

        @property
        def frames(self):
            return JSDebugEvent.Frames(self)

        def __repr__(self):
            s = StringIO()

            try:
                for frame in self.frames:
                    s.write(str(frame))

                return s.getvalue()
            finally:
                s.close()

    class DebugEvent(object):
        pass

    class StateEvent(DebugEvent):
        __state = None

        @property
        def state(self):
            if not self.__state:
                self.__state = JSDebugEvent.State(self.event.executionState())

            return self.__state

    class BreakEvent(StateEvent):
        type = _v8.JSDebugEvent.Break

        def __init__(self, event):
            self.event = event

    class ExceptionEvent(StateEvent):
        type = _v8.JSDebugEvent.Exception

        def __init__(self, event):
            self.event = event

    class NewFunctionEvent(DebugEvent):
        type = _v8.JSDebugEvent.NewFunction

        def __init__(self, event):
            self.event = event

    class Script(object):
        def __init__(self, script):
            self.script = script

        @property
        def source(self):
            return self.script.source()

        @property
        def id(self):
            return self.script.id()

        @property
        def name(self):
            return self.script.name()

        @property
        def lineOffset(self):
            return self.script.lineOffset()

        @property
        def lineCount(self):
            return self.script.lineCount()

        @property
        def columnOffset(self):
            return self.script.columnOffset()

        @property
        def type(self):
            return self.script.type()

        def __repr__(self):
            return "<%s script %s @ %d:%d> : '%s'" % (self.type, self.name,
                                                      self.lineOffset, self.columnOffset,
                                                      self.source)

    class CompileEvent(StateEvent):
        def __init__(self, event):
            self.event = event

        @property
        def script(self):
            if not hasattr(self, "_script"):
                setattr(self, "_script", JSDebugEvent.Script(self.event.script()))

            return self._script

        def __str__(self):
            return str(self.script)

    class BeforeCompileEvent(CompileEvent):
        type = _v8.JSDebugEvent.BeforeCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "before compile script: %s\n%s" % (repr(self.script), repr(self.state))

    class AfterCompileEvent(CompileEvent):
        type = _v8.JSDebugEvent.AfterCompile

        def __init__(self, event):
            JSDebugEvent.CompileEvent.__init__(self, event)

        def __repr__(self):
            return "after compile script: %s\n%s" % (repr(self.script), repr(self.state))

    onMessage = None
    onBreak = None
    onException = None
    onNewFunction = None
    onBeforeCompile = None
    onAfterCompile = None


class JSDebugger(JSDebugProtocol, JSDebugEvent):
    def __init__(self):
        JSDebugProtocol.__init__(self)
        JSDebugEvent.__init__(self)

    def __enter__(self):
        self.enabled = True

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.enabled = False

    @property
    def context(self):
        if not hasattr(self, '_context'):
            self._context = JSContext(ctxt=_v8.debug().context)

        return self._context

    def isEnabled(self):
        return _v8.debug().enabled

    def setEnabled(self, enable):
        dbg = _v8.debug()

        if enable:
            dbg.onDebugEvent = self.onDebugEvent
            dbg.onDebugMessage = self.onDebugMessage
            dbg.onDispatchDebugMessages = self.onDispatchDebugMessages
        else:
            dbg.onDebugEvent = None
            dbg.onDebugMessage = None
            dbg.onDispatchDebugMessages = None

        dbg.enabled = enable

    enabled = property(isEnabled, setEnabled)

    def onDebugMessage(self, msg, data):
        if self.onMessage:
            self.onMessage(json.loads(msg))

    def onDebugEvent(self, type, state, evt):
        if type == JSDebugEvent.Break:
            if self.onBreak: self.onBreak(JSDebugEvent.BreakEvent(evt))
        elif type == JSDebugEvent.Exception:
            if self.onException: self.onException(JSDebugEvent.ExceptionEvent(evt))
        elif type == JSDebugEvent.NewFunction:
            if self.onNewFunction: self.onNewFunction(JSDebugEvent.NewFunctionEvent(evt))
        elif type == JSDebugEvent.BeforeCompile:
            if self.onBeforeCompile: self.onBeforeCompile(JSDebugEvent.BeforeCompileEvent(evt))
        elif type == JSDebugEvent.AfterCompile:
            if self.onAfterCompile: self.onAfterCompile(JSDebugEvent.AfterCompileEvent(evt))

    def onDispatchDebugMessages(self):
        return True

    def debugBreak(self):
        _v8.debug().debugBreak()

    def debugBreakForCommand(self):
        _v8.debug().debugBreakForCommand()

    def cancelDebugBreak(self):
        _v8.debug().cancelDebugBreak()

    def processDebugMessages(self):
        _v8.debug().processDebugMessages()

    def sendCommand(self, cmd, *args, **kwds):
        request = json.dumps({
            'seq': self.nextSeq(),
            'type': 'request',
            'command': cmd,
            'arguments': kwds
        })

        _v8.debug().sendCommand(request)

        return request

    def debugContinue(self, action='next', steps=1):
        return self.sendCommand('continue', stepaction=action)

    def stepNext(self, steps=1):
        """Step to the next statement in the current function."""
        return self.debugContinue(action='next', steps=steps)

    def stepIn(self, steps=1):
        """Step into new functions invoked or the next statement in the current function."""
        return self.debugContinue(action='in', steps=steps)

    def stepOut(self, steps=1):
        """Step out of the current function."""
        return self.debugContinue(action='out', steps=steps)

    def stepMin(self, steps=1):
        """Perform a minimum step in the current function."""
        return self.debugContinue(action='out', steps=steps)
