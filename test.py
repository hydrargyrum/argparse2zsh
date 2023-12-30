#!/usr/bin/env pytest
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser

from argparse2zsh import convert


def test_long():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("--foo")
	parser.add_argument("--bar", help="the bar help")
	parser.add_argument("--bool", help="bool flag", action="store_true")

	assert convert(parser, wrap=False) == "_arguments -s -S '--foo=: :' '--bar=[the bar help]: :' '--bool[bool flag]'"


def test_short():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("-f")
	parser.add_argument("-b", help="the B help")
	parser.add_argument("-a", action="store_true", help="bool flag")

	assert convert(parser, wrap=False) == "_arguments -s -S '-f+: :' '-b+[the B help]: :' '-a[bool flag]'"


def test_repeat():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("-f", action="append")

	assert convert(parser, wrap=False) == "_arguments -s -S '*-f+: :'"


def test_positional():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("foo", help="foo arg")
	parser.add_argument("files", nargs="+", help="the files")

	assert convert(parser, wrap=False) == "_arguments -s -S ':foo arg:' ':the files:_files' '*:the files:_files'"


def test_choices():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("--foo", choices=["FOO", "BAR"])

	assert convert(parser, wrap=False) == "_arguments -s -S '--foo=: :(FOO BAR)'"
