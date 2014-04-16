from v8 import JSContext, JSEngine
from v8.ast import AST

try:
    import json
except ImportError:
    import simplejson as json

class TestAST:

    class Checker(object):
        def __init__(self, testcase):
            self.testcase = testcase
            self.called = []

        def __enter__(self):
            self.ctxt = JSContext()
            self.ctxt.enter()

            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.ctxt.leave()

        def __getattr__(self, name):
            return getattr(self.testcase, name)

        def test(self, script):
            JSEngine().compile(script).visit(self)

            return self.called

        def onProgram(self, prog):
            self.ast = prog.toAST()
            self.json = json.loads(prog.toJSON())

            for decl in prog.scope.declarations:
                decl.visit(self)

            for stmt in prog.body:
                stmt.visit(self)

        def onBlock(self, block):
            for stmt in block.statements:
                stmt.visit(self)

        def onExpressionStatement(self, stmt):
            stmt.expression.visit(self)

            #print type(stmt.expression), stmt.expression

    def testBlock(self):
        class BlockChecker(TestAST.Checker):
            def onBlock(self, stmt):
                self.called.append('block')

                assert AST.NodeType.Block == stmt.type

                assert stmt.initializerBlock
                assert not stmt.anonymous

                target = stmt.breakTarget
                assert target
                assert not target.bound
                assert target.unused
                assert not target.linked

                assert 2 == len(stmt.statements)

                assert ['%InitializeVarGlobal("i", 0);', '%InitializeVarGlobal("j", 0);'] ==\
                        [str(s) for s in stmt.statements]

        with BlockChecker(self) as checker:
            assert ['block'] == checker.test("var i, j;")
            assert """FUNC
. NAME ""
. INFERRED NAME ""
. DECLS
. . VAR "i"
. . VAR "j"
. BLOCK INIT
. . EXPRESSION STATEMENT
. . . CALL RUNTIME
. . . . NAME InitializeVarGlobal
. . . . LITERAL "i"
. . . . LITERAL 0
. . EXPRESSION STATEMENT
. . . CALL RUNTIME
. . . . NAME InitializeVarGlobal
. . . . LITERAL "j"
. . . . LITERAL 0
""" == checker.ast

            assert [u'FunctionLiteral', {u'name': u''},
                [u'Declaration', {u'mode': u'VAR'},
                    [u'Variable', {u'name': u'i'}]
                ], [u'Declaration', {u'mode':u'VAR'},
                    [u'Variable', {u'name': u'j'}]
                ], [u'Block',
                    [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                        [u'Literal', {u'handle':u'i'}],
                        [u'Literal', {u'handle': 0}]]],
                    [u'ExpressionStatement', [u'CallRuntime', {u'name': u'InitializeVarGlobal'},
                        [u'Literal', {u'handle': u'j'}],
                        [u'Literal', {u'handle': 0}]]]
                ]
            ] == checker.json

    def testIfStatement(self):
        class IfStatementChecker(TestAST.Checker):
            def onIfStatement(self, stmt):
                self.called.append('if')

                assert stmt
                assert AST.NodeType.IfStatement == stmt.type

                assert 7 == stmt.pos

                assert stmt.hasThenStatement
                assert stmt.hasElseStatement

                assert "((value % 2) == 0)" == str(stmt.condition)
                assert "{ s = \"even\"; }" == str(stmt.thenStatement)
                assert "{ s = \"odd\"; }" == str(stmt.elseStatement)

                assert not stmt.condition.isPropertyName

        with IfStatementChecker(self) as checker:
            assert ['if'] == checker.test("var s; if (value % 2 == 0) { s = 'even'; } else { s = 'odd'; }")

    def testForStatement(self):
        class ForStatementChecker(TestAST.Checker):
            def onForStatement(self, stmt):
                self.called.append('for')

                assert "{ j += i; }" == str(stmt.body)

                assert "i = 0;" == str(stmt.init)
                assert "(i < 10)" == str(stmt.condition)
                assert "(i++);" == str(stmt.nextStmt)

                target = stmt.continueTarget

                assert target
                assert not target.bound
                assert target.unused
                assert not target.linked
                assert not stmt.fastLoop

            def onForInStatement(self, stmt):
                self.called.append('forIn')

                assert "{ out += name; }" == str(stmt.body)

                assert "name" == str(stmt.each)
                assert "names" == str(stmt.enumerable)

            def onWhileStatement(self, stmt):
                self.called.append('while')

                assert "{ i += 1; }" == str(stmt.body)

                assert "(i < 10)" == str(stmt.condition)

            def onDoWhileStatement(self, stmt):
                self.called.append('doWhile')

                assert "{ i += 1; }" == str(stmt.body)

                assert "(i < 10)" == str(stmt.condition)
                assert 283 == stmt.condition.pos

        with ForStatementChecker(self) as checker:
            assert ['for', 'forIn', 'while', 'doWhile'] == checker.test("""
                var i, j;

                for (i=0; i<10; i++) { j+=i; }

                var names = new Array();
                var out = '';

                for (name in names) { out += name; }

                while (i<10) { i += 1; }

                do { i += 1; } while (i<10);
            """)

    def testCallStatements(self):
        class CallStatementChecker(TestAST.Checker):
            def onVariableDeclaration(self, decl):
                self.called.append('var')

                var = decl.proxy

                if var.name == 's':
                    assert AST.VarMode.var == decl.mode

                    assert var.isValidLeftHandSide
                    assert not var.isArguments
                    assert not var.isThis

            def onFunctionDeclaration(self, decl):
                self.called.append('func')

                var = decl.proxy

                if var.name == 'hello':
                    assert AST.VarMode.var == decl.mode
                    assert decl.function
                    assert '(function hello(name) { s = ("Hello " + name); })' == str(decl.function)
                elif var.name == 'dog':
                    assert AST.VarMode.var == decl.mode
                    assert decl.function
                    assert '(function dog(name) { (this).name = name; })' == str(decl.function)

            def onCall(self, expr):
                self.called.append('call')

                assert "hello" == str(expr.expression)
                assert ['"flier"'] == [str(arg) for arg in expr.args]
                assert 159 == expr.pos

            def onCallNew(self, expr):
                self.called.append('callNew')

                assert "dog" == str(expr.expression)
                assert ['"cat"'] == [str(arg) for arg in expr.args]
                assert 191 == expr.pos

            def onCallRuntime(self, expr):
                self.called.append('callRuntime')

                assert "InitializeVarGlobal" == expr.name
                assert ['"s"', '0'] == [str(arg) for arg in expr.args]
                assert not expr.isJsRuntime

        with CallStatementChecker(self) as checker:
            assert ['var', 'func', 'func', 'callRuntime', 'call', 'callNew'] == checker.test("""
                var s;
                function hello(name) { s = "Hello " + name; }
                function dog(name) { this.name = name; }
                hello("flier");
                new dog("cat");
            """)

    def testTryStatements(self):
        class TryStatementsChecker(TestAST.Checker):
            def onThrow(self, expr):
                self.called.append('try')

                assert '"abc"' == str(expr.exception)
                assert 66 == expr.pos

            def onTryCatchStatement(self, stmt):
                self.called.append('catch')

                assert "{ throw \"abc\"; }" == str(stmt.tryBlock)
                #FIXME assert [] == stmt.targets

                stmt.tryBlock.visit(self)

                assert "err" == str(stmt.variable.name)
                assert "{ s = err; }" == str(stmt.catchBlock)

            def onTryFinallyStatement(self, stmt):
                self.called.append('finally')

                assert "{ throw \"abc\"; }" == str(stmt.tryBlock)
                #FIXME assert [] == stmt.targets

                assert "{ s += \".\"; }" == str(stmt.finallyBlock)

        with TryStatementsChecker(self) as checker:
            assert ['catch', 'try', 'finally'] == checker.test("""
                var s;
                try {
                    throw "abc";
                }
                catch (err) {
                    s = err;
                };

                try {
                    throw "abc";
                }
                finally {
                    s += ".";
                }
            """)

    def testLiterals(self):
        class LiteralChecker(TestAST.Checker):
            def onCallRuntime(self, expr):
                expr.args[1].visit(self)

            def onLiteral(self, litr):
                self.called.append('literal')

                assert not litr.isPropertyName
                assert not litr.isNull
                assert not litr.isTrue

            def onRegExpLiteral(self, litr):
                self.called.append('regex')

                assert "test" == litr.pattern
                assert "g" == litr.flags

            def onObjectLiteral(self, litr):
                self.called.append('object')
                assert 'constant:"name"="flier",constant:"sex"=true' ==\
                       ",".join(["%s:%s=%s" % (prop.kind, prop.key, prop.value) for prop in litr.properties])

            def onArrayLiteral(self, litr):
                self.called.append('array')
                assert '"hello","world",42' ==\
                       ",".join([str(value) for value in litr.values])

        with LiteralChecker(self) as checker:
            assert ['literal', 'regex', 'literal', 'literal'] == checker.test("""
                false;
                /test/g;
                var o = { name: 'flier', sex: true };
                var a = ['hello', 'world', 42];
            """)

    def testOperations(self):
        class OperationChecker(TestAST.Checker):
            def onUnaryOperation(self, expr):
                self.called.append('unaryOp')

                assert AST.Op.BIT_NOT == expr.op
                assert "i" == expr.expression.name

                #print "unary", expr

            def onIncrementOperation(self, expr):
                self.fail()

            def onBinaryOperation(self, expr):
                self.called.append('binOp')

                if expr.op == AST.Op.BIT_XOR:
                    assert "i" == str(expr.left)
                    assert "-1" == str(expr.right)
                    assert 124 == expr.pos
                else:
                    assert "i" == str(expr.left)
                    assert "j" == str(expr.right)
                    assert 36 == expr.pos

            def onAssignment(self, expr):
                self.called.append('assign')

                assert AST.Op.ASSIGN_ADD == expr.op
                assert AST.Op.ADD == expr.binop

                assert "i" == str(expr.target)
                assert "1" == str(expr.value)
                assert 53 == expr.pos

                assert "(i + 1)" == str(expr.binOperation)

                assert expr.compound

            def onCountOperation(self, expr):
                self.called.append('countOp')

                assert not expr.prefix
                assert expr.postfix

                assert AST.Op.INC == expr.op
                assert AST.Op.ADD == expr.binop
                assert 71 == expr.pos
                assert "i" == expr.expression.name

                #print "count", expr

            def onCompareOperation(self, expr):
                self.called.append('compOp')

                if len(self.called) == 4:
                    assert AST.Op.EQ == expr.op
                    assert 88 == expr.pos # i==j
                else:
                    assert AST.Op.EQ_STRICT == expr.op
                    assert 106 == expr.pos # i===j

                assert "i" == str(expr.left)
                assert "j" == str(expr.right)

                #print "comp", expr

            def onConditional(self, expr):
                self.called.append('conditional')

                assert "(i > j)" == str(expr.condition)
                assert "i" == str(expr.thenExpr)
                assert "j" == str(expr.elseExpr)

                assert 144 == expr.thenExpr.pos
                assert 146 == expr.elseExpr.pos

        with OperationChecker(self) as checker:
            assert ['binOp', 'assign', 'countOp', 'compOp', 'compOp', 'binOp', 'conditional'] == checker.test("""
            var i, j;
            i+j;
            i+=1;
            i++;
            i==j;
            i===j;
            ~i;
            i>j?i:j;
            """)

    def testSwitchStatement(self):
        class SwitchStatementChecker(TestAST.Checker):
            def onSwitchStatement(self, stmt):
                self.called.append('switch')

                assert 'expr' == stmt.tag.name
                assert 2 == len(stmt.cases)

                case = stmt.cases[0]

                assert not case.isDefault
                assert case.label.isString
                assert 0 == case.bodyTarget.pos
                assert 57 == case.pos
                assert 1 == len(case.statements)

                case = stmt.cases[1]

                assert case.isDefault
                assert None == case.label
                assert 0 == case.bodyTarget.pos
                assert 109 == case.pos
                assert 1 == len(case.statements)

        with SwitchStatementChecker(self) as checker:
            assert ['switch'] == checker.test("""
            switch (expr) {
                case 'flier':
                    break;
                default:
                    break;
            }
            """)
