# -*- coding: utf-8 -*-
import pytest
from v8 import *

def test_multi_namespace():
    assert not bool(JSContext.inContext)
    assert not bool(JSContext.entered)

    class Global(object):
        name = "global"

    g = Global()

    with JSContext(g) as ctxt:
        assert bool(JSContext.inContext)
        assert g.name == str(JSContext.entered.locals.name)
        assert g.name == str(JSContext.current.locals.name)

        class Local(object):
            name = "local"

        l = Local()

        with JSContext(l):
            assert bool(JSContext.inContext)
            assert l.name == str(JSContext.entered.locals.name)
            assert l.name == str(JSContext.current.locals.name)

        assert bool(JSContext.inContext)
        #assert g.name == str(JSContext.entered.locals.name)
        assert g.name == str(JSContext.current.locals.name)

    assert not bool(JSContext.entered)
    assert not bool(JSContext.inContext)

def test_multi_context():
    # Create an environment
    with JSContext() as ctxt0:
        ctxt0.securityToken = "password"

        global0 = ctxt0.locals
        global0.custom = 1234

        assert 1234 == int(global0.custom)

        # Create an independent environment
        with JSContext() as ctxt1:
            ctxt1.securityToken = ctxt0.securityToken

            global1 = ctxt1.locals
            global1.custom = 1234

            with ctxt0:
                assert 1234 == int(global0.custom)
            assert 1234 == int(global1.custom)

            # Now create a new context with the old global
            with JSContext(global1) as ctxt2:
                ctxt2.securityToken = ctxt1.securityToken

                with ctxt1:
                    assert 1234 == int(global1.custom)

@pytest.mark.xfail()
def test_security_checks():
    with JSContext() as env1:
        env1.securityToken = "foo"

        # Create a function in env1.
        env1.eval("spy=function(){return spy;}")

        spy = env1.locals.spy

        assert isinstance(spy, JSFunction)

        # Create another function accessing global objects.
        env1.eval("spy2=function(){return 123;}")

        spy2 = env1.locals.spy2

        assert isinstance(spy2, JSFunction)

        # Switch to env2 in the same domain and invoke spy on env2.
        env2 = JSContext()

        env2.securityToken = "foo"

        with env2:
            result = spy.apply(env2.locals)

            assert isinstance(result, JSFunction)

        env2.securityToken = "bar"

        # Call cross_domain_call, it should throw an exception
        with env2:
            pytest.raises(JSError, spy2.apply, env2.locals)

@pytest.mark.xfail()
def test_cross_domain_delete():
    with JSContext() as env1:
        env2 = JSContext()

        # Set to the same domain.
        env1.securityToken = "foo"
        env2.securityToken = "foo"

        env1.locals.prop = 3

        env2.locals.env1 = env1.locals

        # Change env2 to a different domain and delete env1.prop.
        #env2.securityToken = "bar"

        assert 3 == int(env1.eval("prop"))

        with env2:
            assert 3 == int(env2.eval("this.env1.prop"))
            assert "false" == str(env2.eval("delete env1.prop"))

        # Check that env1.prop still exists.
        assert 3 == int(env1.locals.prop)
