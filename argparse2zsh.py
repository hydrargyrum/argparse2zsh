#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import re
import shlex
import textwrap

# TODO implement exclusive groups

# argparse has:
# - options (often optional) which are named: "my-command --foo --bar"
# - positional arguments, which are unnamed: "my-command foo bar"


def expect_arg(action):
	"""Return True if action requires at least 1 arg"""
	if action.nargs == 0:
		return False
	return True


def is_positional(action):
	"""Return False for "--foo", True for "foo", for sorting"""
	return not action.option_strings


def destmeta_matches(action, s):
	"""Return True if action.dest or action.metavar matches string"""
	return (
		(action.dest and s in action.dest)
		or (action.metavar and s in action.metavar.lower())
	)


def quote_optspec(s, spaces=False, square=True, parens=True, colon=True):
	result = s.replace("\\", r"\\")
	if parens:
		result = re.sub(r"([()])", r"\\\1", result)
	if square:
		result = re.sub(r"([][])", r"\\\1", result)
	if spaces:
		result = result.replace(" ", r"\ ")
	if colon:
		result = result.replace(":", r"\:")
	return result


def build_option_string(action):
	# result is in the form ["-f:message:action", "--foo:message:action"]
	# `parts` is the ["-f:", "--foo:"] part
	parts = []
	# `suffix` is the ":message:action" part
	suffix = []

	for option in action.option_strings:
		# all these options are aliases
		parts.append(quote_optspec(option))

		if expect_arg(action):
			if option.startswith("--"):
				# argparse accepts --foo=42 and --foo 42
				parts[-1] += "="
			elif option.startswith("-"):
				# argparse accepts -f 42 and -f42
				parts[-1] += "+"

		if action.help:
			parts[-1] += f"[{quote_optspec(action.help)}]"

		if expect_arg(action):
			parts[-1] += ":"

		if isinstance(
			action,
			(argparse._AppendAction, argparse._AppendConstAction)
		):
			# tell zsh we can have more of the same argument
			parts[-1] = f"*{parts[-1]}"
		elif len(action.option_strings) > 1:
			# cannot be repeated + option has different aliases?
			# exclude future aliases of the same action
			all_options = [
				quote_optspec(option)
				for option in action.option_strings
			]
			parts[-1] = f"({' '.join(all_options)}){parts[-1]}"

	if not action.option_strings:
		# the action is a positional argument
		if action.nargs is None:
			# by default, it expects an argument
			parts.append(":")
		elif action.nargs == "?":
			parts.append("::")
		elif action.nargs == "*":
			parts.append("*:")
		elif action.nargs == "+":
			parts.extend([":", "*:"])
		elif isinstance(action.nargs, int):
			parts.extend(":" for _ in range(action.nargs))
		else:
			raise NotImplementedError(f"unhandled nargs: {action.nargs}")

	if expect_arg(action):
		if not action.option_strings and action.help:
			suffix.append(quote_optspec(action.help))
		else:
			suffix.append(quote_optspec(action.metavar or action.dest.upper() or " "))

		is_action_type_class = isinstance(action.type, type)

		if action.choices:
			suffix.append(
				":(%s)" % ' '.join(
					quote_optspec(choice, spaces=True)
					for choice in action.choices
				)
			)
		elif action.type in (int, float):
			numbers = ":_numbers"
			if action.default:
				numbers += f" -d {action.default}"
			if action.type is float:
				numbers += " -f"
			suffix.append(numbers)
		elif is_action_type_class and issubclass(action.type, argparse.FileType):
			suffix.append(":_files")
		elif destmeta_matches(action, "file"):
			# just guessing, argparse.FileType is only seldom used
			suffix.append(":_files")
		elif destmeta_matches(action, "dir"):
			suffix.append(":_files -/")
		elif action.type:
			suffix.append(f":{action.type.__name__}")
		else:
			suffix.append(":")

	return [part + "".join(suffix) for part in parts]


def _cleanup_indented(s):
	return textwrap.dedent(s).strip("\n")

# {{{
# f-strings dumbly insert a string into another.
# If the inserted string contains newlines, lines in will be inserted without
# accounting for the indentation level of the "{}" placeholder.

STX = "\x02"
ETX = "\x03"
REINDENT_BLOCK_RE = re.compile(f"{STX}([^{ETX}]*){ETX}", flags=re.DOTALL)


def _prepare_insert(s):
	# delimit a block
	return f"{STX}{s}{ETX}"


def _replacement(match):
	newline = match.string.rfind("\n", 0, match.start())
	indentation = match.string[newline + 1:match.start()]
	# match.string for example: "...\n    \x02foo\nbar\x03\n..."
	# newline ----------------------^
	# match.start() ----------------------^
	# indentation ------------------> ^--^ 4 spaces
	# in the end we want: "...\n    foo\n    bar\n..."
	# fixed = re.sub("\n", f"\n{indentation}", match[1])
	fixed = match[1].replace("\n", f"\n{indentation}")
	return fixed


def _reindent_inserted(s):
	return REINDENT_BLOCK_RE.sub(_replacement, s)


# }}}


class Converter:
	def __init__(self):
		self.functions = {}

	def convert_parser(self, parser, wrap=True, ignored=None, name=""):
		if not name:
			name = "_" + parser.prog

		# -s does completion knowing -x -y is equivalent to -xy
		# -S stops completion of options if "--" is encountered
		zargs = ["_arguments", "-s", "-S", "-C"]
		for action in sorted(parser._actions, key=is_positional):
			if action is ignored:
				continue

			if parser._subparsers and action is parser._subparsers._group_actions[0]:
				continue

			zargs.extend(build_option_string(action))

		if parser._subparsers:
			self.convert_subparsers(parser, parent_name=name)
			zargs.append("1: :->cmds")
			zargs.append("*::arg:->args")

		zargs_str = " ".join(shlex.quote(part) for part in zargs)

		# body = " ".join(zargs) + "\n"

		if parser._subparsers:
			zvalues = ["_values", shlex.quote(f"{name} command")]
			for subcommand, subparser in parser._subparsers._group_actions[0].choices.items():
				zvalues.append(shlex.quote(f"{subcommand}[{subparser.description}]"))

			zcommands = []
			for subcommand in parser._subparsers._group_actions[0].choices:
				zcommands.append(_cleanup_indented(f"""
					{subcommand})
						{name}_{subcommand} ;;
				"""))
			zcommands_str = "\n".join(zcommands)

			body = _cleanup_indented(_reindent_inserted(f"""
				local line state

				{_prepare_insert(zargs_str)}

				case "$state" in
					cmds)
						{_prepare_insert(' '.join(zvalues))}
						;;
					args)
						case "$line[1]" in
							{_prepare_insert(zcommands_str)}
						esac
						;;
				esac
			"""))

		else:
			body = zargs_str

		self.functions[name] = body

	def convert_subparsers(self, parser, parent_name):
		for subcommand, subparser in parser._subparsers._group_actions[0].choices.items():
			self.convert_parser(subparser, name=f"{parent_name}_{subcommand}")

	def assemble(self, parser):
		if len(self.functions) == 1:
			return _cleanup_indented(f"""
				#compdef {parser.prog}

				{self.functions[f'_{parser.prog}']}
			""")

		parts = [f"#compdef _{parser.prog} {parser.prog}"]
		for name, sub_body in self.functions.items():
			body = _cleanup_indented(_reindent_inserted(f"""
				{name or '_' + parser.prog} () {{
					{_prepare_insert(sub_body)}
				}}
			"""))
			parts.append(body)
		return "\n\n".join(parts)


class ZshCompletionAction(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		self._ignore_self = kwargs.pop("ignore_self", False)
		super().__init__(option_strings, dest=argparse.SUPPRESS, nargs=0)

	def __call__(self, parser, namespace, values, option_string=None):
		cvt = Converter()
		cvt.convert_parser(parser)
		print(cvt.assemble(parser))
		parser.exit()


def monkeypatch():
	# force every ArgumentParser.parse_args to have --zsh-completion
	def new_parse_args(self, *args, **kwargs):
		self.add_argument(
			"--zsh-completion", action=ZshCompletionAction,
			ignore_self=True,
		)
		return old_parse_args(self, *args, **kwargs)

	old_parse_args = argparse.ArgumentParser.parse_args
	argparse.ArgumentParser.parse_args = new_parse_args


if __name__ == "__main__":
	import runpy
	import shutil
	import sys

	monkeypatch()
	del sys.argv[0]
	runpy.run_path(shutil.which(sys.argv[0]), run_name="__main__")
