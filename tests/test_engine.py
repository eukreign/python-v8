# -*- coding: utf-8 -*-
import pytest
from v8 import *
from v8.utils import *

if is_py3k:
    def toNativeString(s):
        return s
else:
    def toNativeString(s, encoding='utf-8'):
        return s.encode(encoding) if isinstance(s, unicode) else s

def testClassProperties():
    with JSContext() as ctxt:
        assert str(JSEngine.version.startswith("3."))
        assert not JSEngine.dead

def testCompile():
    with JSContext() as ctxt:
        with JSEngine() as engine:
            s = engine.compile("1+2")

            assert isinstance(s, JSScript)

            assert "1+2" == s.source
            assert 3 == int(s.run())

            pytest.raises(SyntaxError, engine.compile, "1+")

def testPrecompile():
    with JSContext() as ctxt:
        with JSEngine() as engine:
            data = engine.precompile("1+2")

            assert data
            assert 28 == len(data)

            s = engine.compile("1+2", precompiled=data)

            assert isinstance(s, JSScript)

            assert "1+2" == s.source
            assert 3 == int(s.run())

            pytest.raises(SyntaxError, engine.precompile, "1+")

def testUnicodeSource():
    class Global(JSClass):
        var = u'测试'

        def __getattr__(self, name):
            if (name if is_py3k else name.decode('utf-8')) == u'变量':
                return self.var

            return JSClass.__getattr__(self, name)

    g = Global()

    with JSContext(g) as ctxt:
        with JSEngine() as engine:
            src = u"""
            function 函数() { return 变量.length; }

            函数();

            var func = function () {};
            """

            data = engine.precompile(src)

            assert data
            assert 68 == len(data)

            s = engine.compile(src, precompiled=data)

            assert isinstance(s, JSScript)

            assert toNativeString(src) == s.source
            assert 2 == s.run()

            func_name = toNativeString(u'函数')

            assert hasattr(ctxt.locals, func_name)

            func = getattr(ctxt.locals, func_name)

            assert isinstance(func, JSFunction)

            assert func_name == func.name
            assert "" == func.resname
            assert 1 == func.linenum
            assert 0 == func.lineoff
            assert 0 == func.coloff

            var_name = toNativeString(u'变量')

            setattr(ctxt.locals, var_name, u'测试长字符串')

            assert 6 == func()

            assert "func" == ctxt.locals.func.inferredname

def testExtension():
    extSrc = """function hello(name) { return "hello " + name + " from javascript"; }"""
    extJs = JSExtension("hello/javascript", extSrc)

    assert extJs
    assert "hello/javascript" == extJs.name
    assert extSrc == extJs.source
    assert not extJs.autoEnable
    assert extJs.registered

    #TestEngine.extJs = extJs

    with JSContext(extensions=['hello/javascript']) as ctxt:
        assert "hello flier from javascript" == ctxt.eval("hello('flier')")

    # test the auto enable property

    with JSContext() as ctxt:
        pytest.raises(ReferenceError, ctxt.eval, "hello('flier')")

    extJs.autoEnable = True
    assert extJs.autoEnable

    with JSContext() as ctxt:
        assert "hello flier from javascript" == ctxt.eval("hello('flier')")

    extJs.autoEnable = False
    assert not extJs.autoEnable

    with JSContext() as ctxt:
        pytest.raises(ReferenceError, ctxt.eval, "hello('flier')")

    extUnicodeSrc = u"""function helloW(name) { return "hello " + name + " from javascript"; }"""
    extUnicodeJs = JSExtension(u"helloW/javascript", extUnicodeSrc)

    assert extUnicodeJs
    assert "helloW/javascript" == extUnicodeJs.name
    assert toNativeString(extUnicodeSrc) == extUnicodeJs.source
    assert not extUnicodeJs.autoEnable
    assert extUnicodeJs.registered

    #TestEngine.extUnicodeJs = extUnicodeJs

    with JSContext(extensions=['helloW/javascript']) as ctxt:
        assert "hello flier from javascript" == ctxt.eval("helloW('flier')")

        ret = ctxt.eval(u"helloW('世界')")

        assert u"hello 世界 from javascript" == ret if is_py3k else ret.decode('UTF-8')

def testNativeExtension():
    extSrc = "native function hello();"
    extPy = JSExtension("hello/python", extSrc, lambda func: lambda name: "hello " + name + " from python", register=False)
    assert extPy
    assert "hello/python" == extPy.name
    assert extSrc == extPy.source
    assert not extPy.autoEnable
    assert not extPy.registered
    extPy.register()
    assert extPy.registered

    #TestEngine.extPy = extPy

    with JSContext(extensions=['hello/python']) as ctxt:
        assert "hello flier from python" == ctxt.eval("hello('flier')")

def _testSerialize():
    data = None

    assert not JSContext.entered

    with JSContext() as ctxt:
        assert JSContext.entered

        #ctxt.eval("function hello(name) { return 'hello ' + name; }")

        data = JSEngine.serialize()

    assert data
    assert len(data > 0)

    assert not JSContext.entered

    #JSEngine.deserialize()

    assert JSContext.entered

    assert 'hello flier' == JSContext.current.eval("hello('flier');")

def testEval():
    with JSContext() as ctxt:
        assert 3 == int(ctxt.eval("1+2"))

def testGlobal():
    class Global(JSClass):
        version = "1.0"

    with JSContext(Global()) as ctxt:
        vars = ctxt.locals

        # getter
        assert Global.version == str(vars.version)
        assert Global.version == str(ctxt.eval("version"))

        pytest.raises(ReferenceError, ctxt.eval, "nonexists")

        # setter
        assert 2.0 == float(ctxt.eval("version = 2.0"))

        assert 2.0 == float(vars.version)

def testThis():
    class Global(JSClass):
        version = 1.0

    with JSContext(Global()) as ctxt:
        assert "[object Global]" == str(ctxt.eval("this"))

        assert 1.0 == float(ctxt.eval("this.version"))

def testObjectBuildInMethods():
    class Global(JSClass):
        version = 1.0

    with JSContext(Global()) as ctxt:
        assert "[object Global]" == str(ctxt.eval("this.toString()"))
        assert "[object Global]" == str(ctxt.eval("this.toLocaleString()"))
        assert Global.version == float(ctxt.eval("this.valueOf()").version)

        assert bool(ctxt.eval('this.hasOwnProperty("version")'))

        assert not ctxt.eval('this.hasOwnProperty("nonexistent")')

def testPythonWrapper():
    class Global(JSClass):
        s = [1, 2, 3]
        d = {'a': {'b': 'c'}, 'd': ['e', 'f']}

    g = Global()

    with JSContext(g) as ctxt:
        ctxt.eval("""
            s[2] = s[1] + 2;
            s[0] = s[1];
            delete s[1];
        """)
        assert [2, 4] == g.s
        assert 'c' == ctxt.eval("d.a.b")
        assert ['e', 'f'] == ctxt.eval("d.d")
        ctxt.eval("""
            d.a.q = 4
            delete d.d
        """)
        assert 4 == g.d['a']['q']
        assert None == ctxt.eval("d.d")

@pytest.mark.xfail()
def testMemoryAllocationCallback():
    alloc = {}

    def callback(space, action, size):
        alloc[(space, action)] = alloc.setdefault((space, action), 0) + size

    JSEngine.setMemoryAllocationCallback(callback)

    with JSContext() as ctxt:
        assert (JSObjectSpace.Code, JSAllocationAction.alloc) not in alloc

        ctxt.eval("var o = new Array(1000);")

        assert (JSObjectSpace.Code, JSAllocationAction.alloc) in alloc

    JSEngine.setMemoryAllocationCallback(None)

def testOutOfMemory():
    with JSIsolate():
        JSEngine.setMemoryLimit(max_young_space_size=16 * 1024, max_old_space_size=4 * 1024 * 1024)

        with JSContext() as ctxt:
            JSEngine.ignoreOutOfMemoryException()

            ctxt.eval("var a = new Array(); while(true) a.push(a);")

            assert ctxt.hasOutOfMemoryException

            JSEngine.setMemoryLimit()

            JSEngine.collect()

def testStackLimit():
    with JSIsolate():
        JSEngine.setStackLimit(256 * 1024)

        with JSContext() as ctxt:
            oldStackSize = ctxt.eval("var maxStackSize = function(i){try{(function m(){++i&&m()}())}catch(e){return i}}(0); maxStackSize")

    with JSIsolate():
        JSEngine.setStackLimit(512 * 1024)

        with JSContext() as ctxt:
            newStackSize = ctxt.eval("var maxStackSize = function(i){try{(function m(){++i&&m()}())}catch(e){return i}}(0); maxStackSize")

    assert newStackSize > oldStackSize * 2
