#!/usr/bin/env pytest
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser

from argparse2zsh import convert


def test_long():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("--foo")
	parser.add_argument("--bar", help="the bar help")
	parser.add_argument("--bool", help="bool flag [quote me]", action="store_true")

	assert convert(parser, wrap=False) == r"_arguments -s -S --foo=:FOO: '--bar=[the bar help]:BAR:' '--bool[bool flag \[quote me\]]'"


def test_short():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("-:", dest="colon", help="colon: flag")
	parser.add_argument("-f")
	parser.add_argument("-b", help="the B help")
	parser.add_argument("-a", action="store_true", help="bool flag")

	assert convert(parser, wrap=False) == r"_arguments -s -S '-\:+[colon\: flag]:COLON:' -f+:F: '-b+[the B help]:B:' '-a[bool flag]'"


def test_repeat():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("--foo", action="append")

	assert convert(parser, wrap=False) == "_arguments -s -S '*--foo=:FOO:'"


def test_positional():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("foo", help="foo arg")
	parser.add_argument("files", nargs="+", help="the files")

	assert convert(parser, wrap=False) == "_arguments -s -S ':foo arg:' ':the files:_files' '*:the files:_files'"


def test_choices():
	parser = ArgumentParser(add_help=False)
	parser.add_argument("--foo", choices=["BAR", "BAZ", "(QUOTE ME)"])

	assert convert(parser, wrap=False) == r"_arguments -s -S '--foo=:FOO:(BAR BAZ \(QUOTE\ ME\))'"
