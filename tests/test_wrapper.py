# -*- coding: utf-8 -*-
from datetime import *
import pytest
import os
import sys
from v8 import *
from v8.utils import *

if is_py3k:
    def toUnicodeString(s):
        return s
else:
    def toUnicodeString(s, encoding='utf-8'):
        return s if isinstance(s, unicode) else unicode(s, encoding)

def testObject():

    with JSContext() as ctxt:
        o = ctxt.eval("new Object()")

        assert hash(o) > 0

        o1 = o.clone()

        assert hash(o1) == hash(o)
        assert o != o1

    pytest.raises(UnboundLocalError, o.clone)

def testAutoConverter():
    with JSContext() as ctxt:
        ctxt.eval("""
            var_i = 1;
            var_f = 1.0;
            var_s = "test";
            var_b = true;
            var_s_obj = new String("test");
            var_b_obj = new Boolean(true);
            var_f_obj = new Number(1.5);
        """)

        vars = ctxt.locals

        var_i = vars.var_i

        assert var_i
        assert 1 == int(var_i)

        var_f = vars.var_f

        assert var_f
        assert 1.0 == float(vars.var_f)

        var_s = vars.var_s
        assert var_s
        assert "test" == str(vars.var_s)

        var_b = vars.var_b
        assert var_b
        assert bool(var_b)

        assert "test" == vars.var_s_obj
        assert vars.var_b_obj
        assert 1.5 == vars.var_f_obj

        attrs = dir(ctxt.locals)

        assert attrs
        assert "var_i" in attrs
        assert "var_f" in attrs
        assert "var_s" in attrs
        assert "var_b" in attrs
        assert "var_s_obj" in attrs
        assert "var_b_obj" in attrs
        assert "var_f_obj" in attrs

def testExactConverter():
    class MyInteger(int, JSClass):
        pass

    class MyString(str, JSClass):
        pass

    class MyUnicode(unicode, JSClass):
        pass

    class MyDateTime(time, JSClass):
        pass

    class Global(JSClass):
        var_bool = True
        var_int = 1
        var_float = 1.0
        var_str = 'str'
        var_unicode = u'unicode'
        var_datetime = datetime.now()
        var_date = date.today()
        var_time = time()

        var_myint = MyInteger()
        var_mystr = MyString('mystr')
        var_myunicode = MyUnicode('myunicode')
        var_mytime = MyDateTime()

    with JSContext(Global()) as ctxt:
        typename = ctxt.eval("(function (name) { return this[name].constructor.name; })")
        typeof = ctxt.eval("(function (name) { return typeof(this[name]); })")

        assert 'Boolean' == typename('var_bool')
        assert 'Number' == typename('var_int')
        assert 'Number' == typename('var_float')
        assert 'String' == typename('var_str')
        assert 'String' == typename('var_unicode')
        assert 'Date' == typename('var_datetime')
        assert 'Date' == typename('var_date')
        assert 'Date' == typename('var_time')

        assert 'MyInteger' == typename('var_myint')
        assert 'MyString' == typename('var_mystr')
        assert 'MyUnicode' == typename('var_myunicode')
        assert 'MyDateTime' == typename('var_mytime')

        assert 'object' == typeof('var_myint')
        assert 'object' == typeof('var_mystr')
        assert 'object' == typeof('var_myunicode')
        assert 'object' == typeof('var_mytime')

def testJavascriptWrapper():
    with JSContext() as ctxt:
        assert type(None) == type(ctxt.eval("null"))
        assert type(None) == type(ctxt.eval("undefined"))
        assert bool == type(ctxt.eval("true"))
        assert str == type(ctxt.eval("'test'"))
        assert int == type(ctxt.eval("123"))
        assert float == type(ctxt.eval("3.14"))
        assert datetime == type(ctxt.eval("new Date()"))
        assert JSArray == type(ctxt.eval("[1, 2, 3]"))
        assert JSFunction == type(ctxt.eval("(function() {})"))
        assert JSObject == type(ctxt.eval("new Object()"))

def test_python_wrapper():
    with JSContext() as ctxt:
        typeof = ctxt.eval("(function type(value) { return typeof value; })")
        protoof = ctxt.eval("(function protoof(value) { return Object.prototype.toString.apply(value); })")

        assert '[object Null]' == protoof(None)
        assert 'boolean' == typeof(True)
        assert 'number' == typeof(123)
        assert 'number' == typeof(3.14)
        assert 'string' == typeof('test')
        assert 'string' == typeof(u'test')

        assert '[object Date]' == protoof(datetime.now())
        assert '[object Date]' == protoof(date.today())
        assert '[object Date]' == protoof(time())

        def test():
            pass

        assert '[object Function]' == protoof(abs)
        assert '[object Function]' == protoof(test)
        assert '[object Function]' == protoof(test_python_wrapper)
        assert '[object Function]' == protoof(int)

def testFunction():
    with JSContext() as ctxt:
        func = ctxt.eval("""
            (function ()
            {
                function a()
                {
                    return "abc";
                }

                return a();
            })
            """)

        assert "abc" == str(func())
        assert func != None
        assert not (func == None)

        func = ctxt.eval("(function test() {})")

        assert "test" == func.name
        assert "" == func.resname
        assert 0 == func.linenum
        assert 14 == func.colnum
        assert 0 == func.lineoff
        assert 0 == func.coloff

        #TODO fix me, why the setter doesn't work?
        # func.name = "hello"
        # it seems __setattr__ was called instead of CJavascriptFunction::SetName

        func.setName("hello")

        assert "hello" == func.name

def testCall():
    class Hello(object):
        def __call__(self, name):
            return "hello " + name

    class Global(JSClass):
        hello = Hello()

    with JSContext(Global()) as ctxt:
        assert "hello flier" == ctxt.eval("hello('flier')")

def testJSFunction():
    with JSContext() as ctxt:
        hello = ctxt.eval("(function (name) { return 'hello ' + name; })")

        assert isinstance(hello, JSFunction)
        assert "hello flier" == hello('flier')
        assert "hello flier" == hello.invoke(['flier'])

        obj = ctxt.eval("({ 'name': 'flier', 'hello': function (name) { return 'hello ' + name + ' from ' + this.name; }})")
        hello = obj.hello
        assert isinstance(hello, JSFunction)
        assert "hello flier from flier" == hello('flier')

        tester = ctxt.eval("({ 'name': 'tester' })")
        assert "hello flier from tester" == hello.apply(tester, ['flier'])
        assert "hello flier from json" == hello.apply({ 'name': 'json' }, ['flier'])

def testConstructor():
    with JSContext() as ctx:
        ctx.eval("""
            var Test = function() {
                this.trySomething();
            };
            Test.prototype.trySomething = function() {
                this.name = 'flier';
            };

            var Test2 = function(first_name, last_name) {
                this.name = first_name + ' ' + last_name;
            };
            """)

        assert isinstance(ctx.locals.Test, JSFunction)

        test = JSObject.create(ctx.locals.Test)

        assert isinstance(ctx.locals.Test, JSObject)
        assert "flier" == test.name;

        test2 = JSObject.create(ctx.locals.Test2, ('Flier', 'Lu'))

        assert "Flier Lu" == test2.name;

        test3 = JSObject.create(ctx.locals.Test2, ('Flier', 'Lu'), { 'email': 'flier.lu@gmail.com' })

        assert "flier.lu@gmail.com" == test3.email;

def testJSError():
    with JSContext() as ctxt:
        try:
            ctxt.eval('throw "test"')
            pytest.fail()
        except:
            assert JSError, sys.exc_info([0])

def testErrorInfo():
    with JSContext() as ctxt:
        with JSEngine() as engine:
            try:
                engine.compile("""
                function hello()
                {
                    throw Error("hello world");
                }

                hello();""", "test", 10, 10).run()
                pytest.fail()
            except JSError as e:
                assert str(e).startswith('JSError: Error: hello world ( test @ 14 : 26 )  ->')
                assert "Error" == e.name
                assert "hello world" == e.message
                assert "test" == e.scriptName
                assert 14 == e.lineNum
                assert 78 == e.startPos
                assert 79 == e.endPos
                assert 26 == e.startCol
                assert 27 == e.endCol
                assert 'throw Error("hello world");' == e.sourceLine.strip()
                assert 'Error: hello world\n' +\
                                 '    at Error (native)\n' +\
                                 '    at hello (test:14:27)\n' +\
                                 '    at test:17:17' == e.stackTrace

def testParseStack():
    assert [
        ('Error', 'unknown source', None, None),
        ('test', 'native', None, None),
        ('<anonymous>', 'test0', 3, 5),
        ('f', 'test1', 2, 19),
        ('g', 'test2', 1, 15),
        (None, 'test3', 1, None),
        (None, 'test3', 1, 1),
    ] == JSError.parse_stack("""Error: err
        at Error (unknown source)
        at test (native)
        at new <anonymous> (test0:3:5)
        at f (test1:2:19)
        at g (test2:1:15)
        at test3:1
        at test3:1:1""")

def testStackTrace():
    class Global(JSClass):
        def GetCurrentStackTrace(self, limit):
            return JSStackTrace.GetCurrentStackTrace(4, JSStackTrace.Options.Detailed)

    with JSContext(Global()) as ctxt:
        st = ctxt.eval("""
            function a()
            {
                return GetCurrentStackTrace(10);
            }
            function b()
            {
                return eval("a()");
            }
            function c()
            {
                return new b();
            }
        c();""", "test")

        assert 4 == len(st)
        assert "\tat a (test:4:24)\n\tat (eval)\n\tat b (test:8:24)\n\tat c (test:12:24)\n" == str(st)
        assert "test.a (4:24)\n. (1:1) eval\ntest.b (8:24) constructor\ntest.c (12:24)" ==\
                          "\n".join(["%s.%s (%d:%d)%s%s" % (
                            f.scriptName, f.funcName, f.lineNum, f.column,
                            ' eval' if f.isEval else '',
                            ' constructor' if f.isConstructor else '') for f in st])

def testPythonException():
    class Global(JSClass):
        def raiseException(self):
            raise RuntimeError("Hello")

    with JSContext(Global()) as ctxt:
        r = ctxt.eval("""
            msg ="";
            try
            {
                this.raiseException()
            }
            catch(e)
            {
                msg += "catch " + e + ";";
            }
            finally
            {
                msg += "finally";
            }""")
        assert "catch Error: Hello;finally" == str(ctxt.locals.msg)

def testExceptionMapping():
    class TestException(Exception):
        pass

    class Global(JSClass):
        def raiseIndexError(self):
            return [1, 2, 3][5]

        def raiseAttributeError(self):
            None.hello()

        def raiseSyntaxError(self):
            eval("???")

        def raiseTypeError(self):
            int(sys)

        def raiseNotImplementedError(self):
            raise NotImplementedError("Not support")

        def raiseExceptions(self):
            raise TestException()

    with JSContext(Global()) as ctxt:
        ctxt.eval("try { this.raiseIndexError(); } catch (e) { msg = e; }")

        assert "RangeError: list index out of range" == str(ctxt.locals.msg)

        ctxt.eval("try { this.raiseAttributeError(); } catch (e) { msg = e; }")

        assert "ReferenceError: 'NoneType' object has no attribute 'hello'" == str(ctxt.locals.msg)

        ctxt.eval("try { this.raiseSyntaxError(); } catch (e) { msg = e; }")

        assert "SyntaxError: invalid syntax" == str(ctxt.locals.msg)

        ctxt.eval("try { this.raiseTypeError(); } catch (e) { msg = e; }")

        assert "TypeError: int() argument must be a string or a number, not 'module'" == str(ctxt.locals.msg)

        ctxt.eval("try { this.raiseNotImplementedError(); } catch (e) { msg = e; }")

        assert "Error: Not support" == str(ctxt.locals.msg)

        pytest.raises(TestException, ctxt.eval, "this.raiseExceptions();")

def testArray():
    with JSContext() as ctxt:
        array = ctxt.eval("""
            var array = new Array();

            for (i=0; i<10; i++)
            {
                array[i] = 10-i;
            }

            array;
            """)

        assert isinstance(array, JSArray)
        assert 10 == len(array)

        assert 5 in array
        assert 15 not in array

        assert 10 == len(array)

        for i in range(10):
            assert 10-i == array[i]

        array[5] = 0

        assert 0 == array[5]

        del array[5]

        assert None == array[5]

        # array         [10, 9, 8, 7, 6, None, 4, 3, 2, 1]
        # array[4:7]                  4^^^^^^^^^7
        # array[-3:-1]                         -3^^^^^^-1
        # array[0:0]    []

        assert [6, None, 4] == array[4:7]
        assert [3, 2] == array[-3:-1]
        assert [] == array[0:0]

        array[1:3] = [9, 9, 9]

        assert [10, 9, 9, 9, 7, 6, None, 4, 3, 2, 1] == list(array)

        array[5:8] = [8, 8]

        assert [10, 9, 9, 9, 7, 8, 8, 3, 2, 1] == list(array)

        del array[1:4]

        assert [10, 7, 8, 8, 3, 2, 1] == list(array)

        ctxt.locals.array1 = JSArray(5)
        ctxt.locals.array2 = JSArray([1, 2, 3, 4, 5])

        for i in range(len(ctxt.locals.array2)):
            ctxt.locals.array1[i] = ctxt.locals.array2[i] * 10

        ctxt.eval("""
            var sum = 0;

            for (i=0; i<array1.length; i++)
                sum += array1[i]

            for (i=0; i<array2.length; i++)
                sum += array2[i]
            """)

        assert 165 == ctxt.locals.sum

        ctxt.locals.array3 = [1, 2, 3, 4, 5]
        assert ctxt.eval('array3[1] === 2')
        assert ctxt.eval('array3[9] === undefined')

        args = [
            ["a = Array(7); for(i=0; i<a.length; i++) a[i] = i; a[3] = undefined; a[a.length-1]; a", "0,1,2,,4,5,6", [0, 1, 2, None, 4, 5, 6]],
            ["a = Array(7); for(i=0; i<a.length - 1; i++) a[i] = i; a[a.length-1]; a", "0,1,2,3,4,5,", [0, 1, 2, 3, 4, 5, None]],
            ["a = Array(7); for(i=1; i<a.length; i++) a[i] = i; a[a.length-1]; a", ",1,2,3,4,5,6", [None, 1, 2, 3, 4, 5, 6]]
        ]

        for arg in args:
            array = ctxt.eval(arg[0])

            assert arg[1] == str(array)
            assert arg[2] == [array[i] for i in range(len(array))]

        assert 3 == ctxt.eval("(function (arr) { return arr.length; })")(JSArray([1, 2, 3]))
        assert 2 == ctxt.eval("(function (arr, idx) { return arr[idx]; })")(JSArray([1, 2, 3]), 1)
        assert '[object Array]' == ctxt.eval("(function (arr) { return Object.prototype.toString.call(arr); })")(JSArray([1, 2, 3]))
        assert '[object Array]' == ctxt.eval("(function (arr) { return Object.prototype.toString.call(arr); })")(JSArray((1, 2, 3)))
        assert '[object Array]' == ctxt.eval("(function (arr) { return Object.prototype.toString.call(arr); })")(JSArray(range(3)))

        [x for x in JSArray([1,2,3])]

def testMultiDimArray():
    with JSContext() as ctxt:
        ret = ctxt.eval("""
            ({
                'test': function(){
                    return  [
                        [ 1, 'abla' ],
                        [ 2, 'ajkss' ],
                    ]
                }
            })
            """).test()

        assert [[1, 'abla'], [2, 'ajkss']] == convert(ret)

def testLazyConstructor():
    class Globals(JSClass):
        def __init__(self):
            self.array=JSArray([1,2,3])

    with JSContext(Globals()) as ctxt:
        assert 2 == ctxt.eval("""array[1]""")

def testForEach():
    class NamedClass(object):
        foo = 1

        def __init__(self):
            self.bar = 2

        @property
        def foobar(self):
            return self.foo + self.bar

    def gen(x):
        for i in range(x):
            yield i

    with JSContext() as ctxt:
        func = ctxt.eval("""(function (k) {
            var result = [];
            for (var prop in k) {
              result.push(prop);
            }
            return result;
        })""")

        assert set(["bar", "foo", "foobar"]).issubset(set(func(NamedClass())))
        assert ["0", "1", "2"] == list(func([1, 2, 3]))
        assert ["0", "1", "2"] == list(func((1, 2, 3)))
        assert ["1", "2", "3"] == list(func({1:1, 2:2, 3:3}))

        assert ["0", "1", "2"] == list(func(gen(3)))

def testDict():
    with JSContext() as ctxt:
        obj = ctxt.eval("var r = { 'a' : 1, 'b' : 2 }; r")

        assert 1 == obj.a
        assert 2 == obj.b

        assert { 'a' : 1, 'b' : 2 } == dict(obj)

        assert {'a': 1,
                'b': [1, 2, 3],
                'c': {'str' : 'goofy',
                      'float' : 1.234,
                      'obj' : { 'name': 'john doe' }},
                'd': True,
                'e': None } ==\
                     convert(ctxt.eval("""var x =
                     { a: 1,
                       b: [1, 2, 3],
                       c: { str: 'goofy',
                            float: 1.234,
                            obj: { name: 'john doe' }},
                       d: true,
                       e: null }; x"""))

def testDate():
    with JSContext() as ctxt:
        now1 = ctxt.eval("new Date();")

        assert now1

        now2 = datetime.now()

        delta = now2 - now1 if now2 > now1 else now1 - now2

        assert delta < timedelta(seconds=1)

        func = ctxt.eval("(function (d) { return d.toString(); })")

        now = datetime.now()

        assert str(func(now).startswith(now.strftime("%a %b %d %Y %H:%M:%S")))

        ctxt.eval("function identity(x) { return x; }")
        # JS only has millisecond resolution, so cut it off there
        now3 = now2.replace(microsecond=123000)
        assert now3 == ctxt.locals.identity(now3)

def testUnicode():
    with JSContext() as ctxt:
        assert u"人" == toUnicodeString(ctxt.eval(u"\"人\""))
        assert u"é" == toUnicodeString(ctxt.eval(u"\"é\""))

        func = ctxt.eval("(function (msg) { return msg.length; })")

        assert 2 == func(u"测试")

def testClassicStyleObject():
    class FileSystemWarpper:
        @property
        def cwd(self):
            return os.getcwd()

    class Global:
        @property
        def fs(self):
            return FileSystemWarpper()

    with JSContext(Global()) as ctxt:
        assert os.getcwd() == ctxt.eval("fs.cwd")

def testRefCount():
    count = sys.getrefcount(None)

    class Global(JSClass):
        pass

    g = Global()
    g_refs = sys.getrefcount(g)

    with JSContext(g) as ctxt:
        ctxt.eval("""
            var none = null;
        """)
        count_1 = sys.getrefcount(None)

        ctxt.eval("""
            var none = null;
        """)
        count_2 = sys.getrefcount(None)

        # py.test assert creates additional references to None
        # so we save the count before doing any assertions
        assert count+1 == count_1
        assert count+1 == count_2

        del ctxt

    assert g_refs == sys.getrefcount(g)

def testProperty():
    class Global(JSClass):
        def __init__(self, name):
            self._name = name
        def getname(self):
            return self._name
        def setname(self, name):
            self._name = name
        def delname(self):
            self._name = 'deleted'

        name = property(getname, setname, delname)

    g = Global('world')

    with JSContext(g) as ctxt:
        assert 'world' == ctxt.eval("name")
        assert 'flier' == ctxt.eval("this.name = 'flier';")
        assert 'flier' == ctxt.eval("name")
        assert ctxt.eval("delete name")
        ###
        # FIXME replace the global object with Python object
        #
        #assert 'deleted' == ctxt.eval("name")
        #ctxt.eval("__defineGetter__('name', function() { return 'fixed'; });")
        #assert 'fixed' == ctxt.eval("name")

def testGetterAndSetter():
    class Global(JSClass):
       def __init__(self, testval):
           self.testval = testval

    with JSContext(Global("Test Value A")) as ctxt:
       assert "Test Value A" == ctxt.locals.testval
       ctxt.eval("""
           this.__defineGetter__("test", function() {
               return this.testval;
           });
           this.__defineSetter__("test", function(val) {
               this.testval = val;
           });
       """)
       assert "Test Value A" == ctxt.locals.test

       ctxt.eval("test = 'Test Value B';")

       assert "Test Value B" == ctxt.locals.test

@pytest.mark.xfail()
def test_destructor():
    class Hello(object):
        deleted = False
        def say(self): pass
        def __del__(self):
            Hello.deleted = True

    with JSContext() as ctxt:
        fn = ctxt.eval("(function (obj) { obj.say(); })")

        obj = Hello()
        assert 2 == sys.getrefcount(obj)

        fn(obj)
        assert 4 == sys.getrefcount(obj)

    assert not Hello.deleted

    del fn
    del ctxt

    # causes segfault
    # JSEngine.collect()

    assert 2 == sys.getrefcount(obj)

    del obj

    assert Hello.deleted

def testNullInString():
    with JSContext() as ctxt:
        fn = ctxt.eval("(function (s) { return s; })")

        assert "hello \0 world" == fn("hello \0 world")

def testLivingObjectCache():
    class Global(JSClass):
        i = 1
        b = True
        o = object()

    with JSContext(Global()) as ctxt:
        assert ctxt.eval("i == i")
        assert ctxt.eval("b == b")
        assert ctxt.eval("o == o")

def testNamedSetter():
    class Obj(JSClass):
        @property
        def p(self):
            return self._p

        @p.setter
        def p(self, value):
            self._p = value

    class Global(JSClass):
        def __init__(self):
            self.obj = Obj()
            self.d = {}
            self.p = None

    with JSContext(Global()) as ctxt:
        ctxt.eval("""
        x = obj;
        x.y = 10;
        x.p = 10;
        d.y = 10;
        """)
        assert 10 == ctxt.eval("obj.y")
        assert 10 == ctxt.eval("obj.p")
        assert 10 == ctxt.locals.d['y']

def testWatch():
    class Obj(JSClass):
        def __init__(self):
            self.p = 1

    class Global(JSClass):
        def __init__(self):
            self.o = Obj()

    with JSContext(Global()) as ctxt:
        ctxt.eval("""
        o.watch("p", function (id, oldval, newval) {
            return oldval + newval;
        });
        """)

        assert 1 == ctxt.eval("o.p")

        ctxt.eval("o.p = 2;")

        assert 3 == ctxt.eval("o.p")

        ctxt.eval("delete o.p;")

        assert None == ctxt.eval("o.p")

        ctxt.eval("o.p = 2;")

        assert 2 == ctxt.eval("o.p")

        ctxt.eval("o.unwatch('p');")

        ctxt.eval("o.p = 1;")

        assert 1 == ctxt.eval("o.p")

def testReferenceError():
    class Global(JSClass):
        def __init__(self):
            self.s = self

    with JSContext(Global()) as ctxt:
        pytest.raises(ReferenceError, ctxt.eval, 'x')

        assert ctxt.eval("typeof(x) === 'undefined'")

        assert ctxt.eval("typeof(String) === 'function'")

        assert ctxt.eval("typeof(s.String) === 'undefined'")

        assert ctxt.eval("typeof(s.z) === 'undefined'")

def testRaiseExceptionInGetter():
    class Document(JSClass):
        def __getattr__(self, name):
            if name == 'y':
                raise TypeError()

            return JSClass.__getattr__(self, name)

    class Global(JSClass):
        def __init__(self):
            self.document = Document()

    with JSContext(Global()) as ctxt:
        assert None == ctxt.eval('document.x')
        pytest.raises(TypeError, ctxt.eval, 'document.y')

def testUndefined():
    class Global(JSClass):
        def returnNull(self):
            return JSNull()

        def returnUndefined(self):
            return JSUndefined()

        def returnNone(self):
            return None

    with JSContext(Global()) as ctxt:
        assert not bool(JSNull())
        assert not bool(JSUndefined())

        assert "null" == str(JSNull())
        assert "undefined" == str(JSUndefined())

        assert ctxt.eval('null == returnNull()')
        assert ctxt.eval('undefined == returnUndefined()')
        assert ctxt.eval('null == returnNone()')


