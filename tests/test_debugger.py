import pytest
from v8 import *
from v8.debugger import *

class TestDebug:

    def setUp(self):
        self.engine = v8.JSEngine()

    def tearDown(self):
        del self.engine

    events = []

    def processDebugEvent(self, event):
        self.events.append(repr(event))

    def testEventDispatch(self):
        debugger = JSDebugger()
        assert not debugger.enabled

        debugger.onBreak = lambda evt: self.processDebugEvent(evt)
        debugger.onException = lambda evt: self.processDebugEvent(evt)
        debugger.onNewFunction = lambda evt: self.processDebugEvent(evt)
        debugger.onBeforeCompile = lambda evt: self.processDebugEvent(evt)
        debugger.onAfterCompile = lambda evt: self.processDebugEvent(evt)

        with JSContext() as ctxt:
            debugger.enabled = True

            assert 3 == int(ctxt.eval("function test() { text = \"1+2\"; return eval(text) } test()"))

            debugger.enabled = False

            pytest.raises(JSError, JSContext.eval, ctxt, "throw 1")

            assert not debugger.enabled

        assert 4 == len(self.events)
