#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

import argparse
import re
import shlex

# TODO implement subparsers
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
		elif action.type is int:
			suffix.append(":_numbers")
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


def convert(parser, wrap=True, ignored=None):
	# -s does completion knowing -x -y is equivalent to -xy
	# -S stops completion of options if "--" is encountered
	parts = ["_arguments", "-s", "-S"]
	for action in sorted(parser._actions, key=is_positional):
		if action is ignored:
			continue

		parts.extend(build_option_string(action))

	parts = [shlex.quote(part) for part in parts]
	if wrap:
		return " \\\n\t".join(parts)
	return " ".join(parts)


class ZshCompletionAction(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		self._ignore_self = kwargs.pop("ignore_self", False)
		super().__init__(option_strings, dest=argparse.SUPPRESS, nargs=0)

	def __call__(self, parser, namespace, values, option_string=None):
		print(f"#compdef {parser.prog}")
		print(convert(parser, ignored=self))
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
