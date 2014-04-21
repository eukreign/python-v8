#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import os
import os.path
import glob
import subprocess
import traceback
import platform

from distutils.command.build import build as _build
from setuptools import setup, Extension, Command, find_packages
from setuptools.command.develop import develop as _develop
from setuptools.command.test import test as TestCommand
from setuptools.command.easy_install import is_64bit
from distutils.sysconfig import get_config_vars

DEBUG = False

V8_SNAPSHOT_ENABLED = not DEBUG # build using snapshots for faster start-up
V8_NATIVE_REGEXP = True         # Whether to use native or interpreted regexp implementation
V8_OBJECT_PRINT = DEBUG         # enable object printing
V8_EXTRA_CHECKS = DEBUG         # enable extra checks
V8_VERIFY_HEAP = DEBUG          # enable verify heap
V8_GDB_JIT = False              # enable GDB jit
V8_VTUNE_JIT = False
V8_DISASSEMBLEER = DEBUG        # enable the disassembler to inspect generated code
V8_DEBUGGER_SUPPORT = True      # enable debugging of JavaScript code
V8_LIVE_OBJECT_LIST = DEBUG     # enable live object list features in the debugger
V8_WERROR = False               # ignore compile warnings
V8_STRICTALIASING = True        # enable strict aliasing
V8_BACKTRACE = True
V8_I18N = False

IS_64BIT = is_64bit()
IS_ARM = 'arm' in platform.processor()

ARCH = 'x64' if IS_64BIT else 'arm' if IS_ARM else 'ia32'
MODE = 'debug' if DEBUG else 'release'

LIBV8_PATH = "libv8"
LIBV8_SVN_URL = "http://v8.googlecode.com/svn/trunk/"
LIBV8_SVN_REV = 19632

# fixes distutils bug that causes warning when compiling
# c++ with gcc and the -Wstrict-prototypes flag
(opt,) = get_config_vars('OPT')
os.environ['OPT'] = " ".join(
    flag for flag in opt.split() if flag != '-Wstrict-prototypes'
)

## macros

macros = [("BOOST_PYTHON_STATIC_LIB", None)]

if DEBUG:
    macros += [("V8_ENABLE_CHECKS", None)]

if V8_NATIVE_REGEXP:
    macros += [("V8_NATIVE_REGEXP", None)]
else:
    macros += [("V8_INTERPRETED_REGEXP", None)]

if V8_DISASSEMBLEER:
    macros += [("ENABLE_DISASSEMBLER", None)]

if V8_LIVE_OBJECT_LIST:
    V8_OBJECT_PRINT = True
    V8_DEBUGGER_SUPPORT = True
    macros += [("LIVE_OBJECT_LIST", None)]

if V8_OBJECT_PRINT:
    macros += [("OBJECT_PRINT", None)]

if V8_DEBUGGER_SUPPORT:
    macros += [("ENABLE_DEBUGGER_SUPPORT", None)]

if IS_64BIT:
    macros += [("V8_TARGET_ARCH_X64", None)]
elif IS_ARM:
    macros += [("V8_TARGET_ARCH_ARM", None)]
else:
    macros += [("V8_TARGET_ARCH_IA32", None)]

## libs

libraries = [
    'v8_base.' + ARCH,
    'v8_snapshot' if V8_SNAPSHOT_ENABLED else ('v8_nosnapshot.' + ARCH),
    'rt'
]

boost_libs = ['boost_python', 'boost_thread', 'boost_system']
if DEBUG:
    boost_libs = [lib + '-d' for lib in boost_libs]
libraries += boost_libs

library_dirs = [
    "/usr/local/lib",
    "%s/out/%s.%s/obj.target/tools/gyp/" % (LIBV8_PATH, ARCH, MODE)
]
native_path = "%s/out/native/obj.target/tools/gyp/" % LIBV8_PATH
if os.path.isdir(native_path):
    library_dirs.append(native_path)

## include

include_dirs = [
    os.path.join(LIBV8_PATH, 'include'),
    LIBV8_PATH,
    os.path.join(LIBV8_PATH, 'src'),
]
include_dirs += ['/usr/local/include']

## extras

extra_compile_args = []
extra_link_args = []
extra_objects = []
extra_compile_args += ["-Wno-write-strings"]

if IS_64BIT:
    extra_link_args += ["-fPIC"]

extra_link_args += ["-lrt"] # make ubuntu happy

if DEBUG:
    extra_compile_args += ['-g', '-O0', '-fno-inline']
else:
    extra_compile_args += ['-g', '-O3']

if V8_I18N:
    icu_path = "%s/out/%s.%s/obj.target/third_party/icu/" % (LIBV8_PATH, ARCH, MODE)
    extra_objects += ["%slib%s.a" % (icu_path, name) for name in ['icui18n', 'icuuc', 'icudata']]


def ensure_libv8():
    if os.path.isdir(LIBV8_PATH):
        return
    args = (LIBV8_SVN_URL, LIBV8_SVN_REV, LIBV8_PATH)
    exec_cmd("svn export {}@{} {}".format(*args), "fetching libv8")
    exec_cmd("make dependencies", "fetching libv8 dependencies", cwd=LIBV8_PATH)

def exec_cmd(cmdline_or_args, msg, shell=True, cwd=None, env=None, output=False):
    print("-" * 20)
    print("INFO: %s ..." % msg)
    print("DEBUG: > %s" % cmdline_or_args)

    if cwd:
        proc = subprocess.Popen(cmdline_or_args, shell=shell, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        proc = subprocess.Popen(cmdline_or_args, shell=shell, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = proc.communicate()

    succeeded = proc.returncode == 0

    if not succeeded:
        print("ERROR: %s failed: code=%d" % (msg or "Execute command", proc.returncode))
        print("DEBUG: %s" % err)

    return succeeded, out, err if output else succeeded





def build_libv8():
    print("=" * 20)
    print("INFO: Patching the GYP scripts")

    # Next up, we have to patch the SConstruct file from the v8 source to remove -no-rtti and -no-exceptions
    gypi = os.path.join(LIBV8_PATH, "build/standalone.gypi")

    # Check if we need to patch by searching for rtti flag in the data
    with open(gypi, 'r') as f:
        build_script = f.read()

    fixed_build_script = build_script.replace('-fno-rtti', '') \
                                     .replace('-fno-exceptions', '') \
                                     .replace('-Werror', '') \
                                     .replace("'RuntimeTypeInfo': 'false',", "'RuntimeTypeInfo': 'true',") \
                                     .replace("'ExceptionHandling': '0',", "'ExceptionHandling': '1',") \
                                     .replace("'GCC_ENABLE_CPP_EXCEPTIONS': 'NO'", "'GCC_ENABLE_CPP_EXCEPTIONS': 'YES'") \
                                     .replace("'GCC_ENABLE_CPP_RTTI': 'NO'", "'GCC_ENABLE_CPP_RTTI': 'YES'")

    if build_script == fixed_build_script:
        print("INFO: skip to patch the Google v8 build/standalone.gypi file ")
    else:
        print("INFO: patch the Google v8 build/standalone.gypi file to enable RTTI and C++ Exceptions")

        if os.path.exists(gypi + '.bak'):
            os.remove(gypi + '.bak')

        os.rename(gypi, gypi + '.bak')

        with open(gypi, 'w') as f:
            f.write(fixed_build_script)

    options = {
        'disassembler': 'on' if V8_DISASSEMBLEER else 'off',
        'objectprint': 'on' if V8_OBJECT_PRINT else 'off',
        'verifyheap': 'on' if V8_VERIFY_HEAP else 'off',
        'snapshot': 'on' if V8_SNAPSHOT_ENABLED else 'off',
        'extrachecks': 'on' if V8_EXTRA_CHECKS else 'off',
        'gdbjit': 'on' if V8_GDB_JIT else 'off',
        'vtunejit': 'on' if V8_VTUNE_JIT else 'off',
        'liveobjectlist': 'on' if V8_LIVE_OBJECT_LIST else 'off',
        'debuggersupport': 'on' if V8_DEBUGGER_SUPPORT else 'off',
        'regexp': 'native' if V8_NATIVE_REGEXP else 'interpreted',
        'strictaliasing': 'on' if V8_STRICTALIASING else 'off',
        'werror': 'yes' if V8_WERROR else 'no',
        'backtrace': 'on' if V8_BACKTRACE else 'off',
        'i18nsupport': 'on' if V8_I18N else 'off',
        'visibility': 'on',
        'library': 'shared',
    }

    print("=" * 20)

    print("INFO: building Google v8 with GYP for %s platform with %s mode" % (ARCH, MODE))

    options = ' '.join(["%s=%s" % (k, v) for k, v in options.items()])

    cmdline = "make -j 8 %s %s.%s" % (options, ARCH, MODE)

    exec_cmd(cmdline, "build v8 from SVN", cwd=LIBV8_PATH)


def generate_probes():
    build_path = "build"

    if not os.path.exists(build_path):
        print("INFO: automatic make the build folder: %s" % build_path)

        try:
            os.makedirs(build_path, 0755)
        except os.error as ex:
            print("WARN: fail to create the build folder, %s" % ex)

    probes_d = "src/probes.d"
    probes_h = "src/probes.h"
    probes_o = os.path.join(build_path, "probes.o")

    if (exec_cmd("dtrace -h -C -s %s -o %s" % (probes_d, probes_h), "generate DTrace probes.h") and \
        exec_cmd("dtrace -G -C -s %s -o %s" % (probes_d, probes_o), "generate DTrace probes.o")):
        extra_objects.append(probes_o)
    else:
        print("INFO: dtrace or systemtap doesn't works, force to disable probes")

        config_file = "src/Config.h"

        with open(config_file, "r") as f:
            config_settings= f.read()

        modified_config_settings = config_settings.replace("\n#define SUPPORT_PROBES 1", "\n//#define SUPPORT_PROBES 1")

        if modified_config_settings != config_settings:
            if os.path.exists(config_file + '.bak'):
                os.remove(config_file + '.bak')

            os.rename(config_file, config_file + '.bak')

            with open(config_file, 'w') as f:
                f.write(modified_config_settings)


def prepare_v8():
    try:
        ensure_libv8()
        build_libv8()
        generate_probes()
    except Exception as e:
        print("ERROR: fail to checkout and build v8, %s" % e)
        traceback.print_exc()

class build(_build):
    def run(self):
        prepare_v8()

        _build.run(self)


class develop(_develop):
    def run(self):
        prepare_v8()

        _develop.run(self)

python_v8 = Extension(name="_v8",
                 sources=glob.glob("src/*.cpp"),
                 define_macros=macros,
                 include_dirs=include_dirs,
                 library_dirs=library_dirs,
                 libraries=libraries,
                 extra_compile_args=extra_compile_args,
                 extra_link_args=extra_link_args,
                 extra_objects=extra_objects,
                 )

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        raise SystemExit(errno)

setup(
    name="v8",
    version="0.1.4",
    description="Python Wrapper for Google V8 Engine",
    author="Lex Berezhny",
    author_email="lex@damoti.com",
    url="http://github.com/damoti/python-v8",
    license="Apache Software License",
    platforms=["linux", "osx", "cygwin", "win32"],
    packages=find_packages(),
    include_package_data=True,
    tests_require=['pytest'],
    ext_modules=[python_v8],
    cmdclass = {
        "build": build,
        "v8build": _build,
        "develop": develop
    },
    classifiers = [
        "Programming Language :: C++",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Plugins",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    keywords = "js javascript v8"
)
