import contextlib
import functools
import os
import subprocess  # nosec
import sys
import traceback
import typing as tp

import clickfile
import click

SEMVER_RE = r"([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9a-zA-Z-]+))?"
"""Semver regex.

Example: `X.Y.Z` or `X.Y.Z-string`
"""


class Nope(click.ClickException):
    """Warning.
    """

    exit_code = 0

    def show(self, file=None):
        click.echo(yellow(f"Nope: {self.format_message()}"))


class Error(Exception):
    pass


_warn_only = False
_quiet = False


@contextlib.contextmanager
def quiet():
    global _quiet
    prev = _quiet
    try:
        _quiet = True
        yield
    finally:
        _quiet = prev


def quiet_func(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
        return True
    except click.Abort:
        return False


@contextlib.contextmanager
def warn_only():
    global _warn_only
    prev = _warn_only
    try:
        _warn_only = True
        yield
    finally:
        _warn_only = prev


@contextlib.contextmanager
def settings(warn_only=False):
    global _warn_only
    prev = _warn_only
    try:
        _warn_only = warn_only
        yield
    finally:
        _warn_only = prev


def with_pycache_dropped(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        shell(f"find {clickfile.HOME_DIR} -name __pycache__ | xargs rm -rf", check=False)
        return func(*args, **kwargs)

    return wrapper


@contextlib.contextmanager
def lcd(path):
    prev = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev)


@contextlib.contextmanager
def shell_env(**kwargs):
    unset = object()
    prev = {k: os.environ.get(k, unset) for k in kwargs}
    try:
        os.environ.update(kwargs)
        yield
    finally:
        for k, v in prev.items():
            if v is unset:
                del os.environ[k]
            else:
                os.environ[k] = v


@contextlib.contextmanager
def cli_error_handler():
    try:
        yield
    except Exception as err:
        with_trace = not isinstance(err, (subprocess.SubprocessError, Error))
        if with_trace:
            print(red(traceback.format_exc()))
        else:
            print(red(str(err)))
        sys.exit(1)


def num_processes():
    return max(os.cpu_count() // 4, 1)


def is_docker_container():
    """Return True in this code is run inside docker container."""
    return os.path.exists("/.dockerenv")


def shell(*args, **kwargs):
    """Run a command in shell.

    Accepts all arguments that ``subprocess.run()`` does,
    with some extra opinionated defaults:

    ::

        shell: True
        check: True
        encoding: utf-8

    :keyword bool capture: Capture and return stdout (Default: False)
    """
    kwargs["shell"] = True
    if "check" not in kwargs:
        kwargs["check"] = True  # check for exit code
    kwargs["encoding"] = "utf-8"  # open streams in text mode
    if kwargs.pop("capture", False):
        kwargs["stdout"] = subprocess.PIPE
    if _quiet:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    try:
        print(click.style("$ " + args[0].strip(), bold=True))
        proc = subprocess.run(*args, **kwargs)  # nosec
        return proc.stdout.strip() if proc.stdout is not None else None
    except subprocess.CalledProcessError as e:
        if _warn_only:
            print(red(str(e)))
        elif _quiet:
            return
        else:
            raise


def hyphenify(s: str) -> str:
    return s.replace("_", "-")


def unhyphenify(s: str) -> str:
    return s.replace("-", "_")


def header(s):
    print(click.style("\n\n{}\n".format(s), fg="white", bold=True))


def green(s):
    return click.style(s, fg="green")


def yellow(s):
    return click.style(s, fg="yellow")


def red(s):
    return click.style(s, fg="red")


def pprint_list(
    header: str, data: tp.Iterable, colorer: tp.Callable = green, sort: bool = True
) -> None:
    print(colorer(f"{header}"))
    print(colorer(" - " + "\n - ".join(sorted(data) if sort else data)))
    print(colorer(f"({len(data)} objects listed)"))
