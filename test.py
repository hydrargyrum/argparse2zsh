#!/usr/bin/env pytest
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser
from textwrap import dedent

from argparse2zsh import Converter, _prepare_insert, _reindent_inserted


def convert(parser):
	cvt = Converter()
	cvt.convert_parser(parser)
	return cvt.assemble(parser).strip()


def test_long():
	parser = ArgumentParser(add_help=False, prog="app")
	parser.add_argument("--foo")
	parser.add_argument("--bar", help="the bar help")
	parser.add_argument("--bool", help="bool flag [quote me]", action="store_true")

	assert convert(parser) == dedent(r"""
		#compdef app

		_arguments -s -S -C --foo=:FOO: '--bar=[the bar help]:BAR:' '--bool[bool flag \[quote me\]]'
	""").strip()


def test_short():
	parser = ArgumentParser(add_help=False, prog="app")
	parser.add_argument("-:", dest="colon", help="colon: flag")
	parser.add_argument("-f")
	parser.add_argument("-b", help="the B help")
	parser.add_argument("-a", action="store_true", help="bool flag")

	assert convert(parser) == dedent(r"""
		#compdef app

		_arguments -s -S -C '-\:+[colon\: flag]:COLON:' -f+:F: '-b+[the B help]:B:' '-a[bool flag]'
	""").strip()


def test_repeat():
	parser = ArgumentParser(add_help=False, prog="test")
	parser.add_argument("--foo", action="append")

	assert convert(parser) == dedent(r"""
		#compdef test

		_arguments -s -S -C '*--foo=:FOO:'
	""").strip()


def test_types():
	parser = ArgumentParser(add_help=False, prog="test")
	parser.add_argument("--digit", type=int, default=42)
	parser.add_argument("--fract", type=float)
	parser.add_argument("--something", metavar="FILE")

	assert convert(parser) == dedent(r"""
		#compdef test

		_arguments -s -S -C '--digit=:DIGIT:_numbers -d 42' '--fract=:FRACT:_numbers -f' --something=:FILE:_files
	""").strip()


def test_positional():
	parser = ArgumentParser(add_help=False, prog="test")
	parser.add_argument("foo", help="foo arg")
	parser.add_argument("files", nargs="+", help="the files")

	assert convert(parser) == dedent(r"""
		#compdef test

		_arguments -s -S -C ':foo arg:' ':the files:_files' '*:the files:_files'
	""").strip()


def test_choices():
	parser = ArgumentParser(add_help=False, prog="test")
	parser.add_argument("--foo", choices=["BAR", "BAZ", "(QUOTE ME)"])

	assert convert(parser) == dedent(r"""
		#compdef test

		_arguments -s -S -C '--foo=:FOO:(BAR BAZ \(QUOTE\ ME\))'
	""").strip()


def test_exclude_aliases():
	parser = ArgumentParser(add_help=False, prog="test")
	parser.add_argument("-f", "--foo", action="store_true")

	assert convert(parser) == dedent(r"""
		#compdef test

		_arguments -s -S -C '(-f --foo)-f' '(-f --foo)--foo'
	""").strip()


def test_subparser():
	parser = ArgumentParser(add_help=False, prog="main")
	parser.add_argument("--common", action="store_true")
	subs = parser.add_subparsers()
	sub = subs.add_parser("foo", add_help=False)
	sub.add_argument("--opt", action="store_true")

	assert convert(parser) == dedent(r"""
		#compdef _main main

		_main_foo () {
			_arguments -s -S -C --opt
		}

		_main () {
			local line state

			_arguments -s -S -C --common '1: :->cmds' '*::arg:->args'

			case "$state" in
				cmds)
					_values '_main command' 'foo[None]'
					;;
				args)
					case "$line[1]" in
						foo)
							_main_foo ;;
					esac
					;;
			esac
		}
	""").strip()


def test_rebuild():
	inserted = "this\nis\nindented\n\tmore"
	s = _reindent_inserted(f"""
		start
		of
		line
			indented

		inject:
			{_prepare_insert(inserted)}
	""")
	s = dedent(s)
	assert s == dedent("""
		start
		of
		line
			indented

		inject:
			this
			is
			indented
				more
	""")
