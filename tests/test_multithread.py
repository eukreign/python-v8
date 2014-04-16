# -*- coding: utf-8 -*-
import pytest
from v8 import *

def test_locker():
    assert not JSLocker.active
    assert not JSLocker.locked

    with JSLocker() as outter_locker:
        assert JSLocker.active
        assert JSLocker.locked

        assert outter_locker

        with JSLocker() as inner_locker:
            assert JSLocker.locked

            assert outter_locker
            assert inner_locker

            with JSUnlocker() as unlocker:
                assert not JSLocker.locked

                assert outter_locker
                assert inner_locker

            assert JSLocker.locked

    assert JSLocker.active
    assert not JSLocker.locked

    locker = JSLocker()

    with JSContext():
        pytest.raises(RuntimeError, locker.__enter__)
        pytest.raises(RuntimeError, locker.__exit__, None, None, None)

    del locker

def test_multi_python_thread():
    import time, threading

    class Global:
        count = 0
        started = threading.Event()
        finished = threading.Semaphore(0)

        def sleep(self, ms):
            time.sleep(ms / 1000.0)

            self.count += 1

    g = Global()

    def run():
        with JSContext(g) as ctxt:
            ctxt.eval("""
                started.wait();

                for (i=0; i<10; i++)
                {
                    sleep(100);
                }

                finished.release();
            """)

    threading.Thread(target=run).start()

    now = time.time()

    assert 0 == g.count

    g.started.set()
    g.finished.acquire()

    assert 10 == g.count

    assert (time.time() - now) >= 1

def test_multi_javascript_thread():
    import time, threading

    class Global:
        result = []

        def add(self, value):
            with JSUnlocker():
                time.sleep(0.1)
                self.result.append(value)

    g = Global()

    def run():
        with JSContext(g) as ctxt:
            ctxt.eval("""
                for (i=0; i<10; i++)
                    add(i);
            """)

    threads = [threading.Thread(target=run), threading.Thread(target=run)]

    with JSLocker():
        for t in threads: t.start()

    for t in threads: t.join()

    assert 20 == len(g.result)
