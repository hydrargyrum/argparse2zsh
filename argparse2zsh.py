#!/usr/bin/env python3

import argparse
import shlex

# TODO implement subparsers


r"""
OPT[DESCRIPTION]:MESSAGE:ACTION

(ITEM1 ITEM2)
((ITEM1\:’DESC1’ ITEM2\:’DESC2’))
FUNCTION	Name of a function to call for generating matches or performing some other action, e.g. _files or _message
{EVAL-STRING}	Evaluate string as shell code to generate matches. This can be used to call a utility function with arguments, e.g. _values or _describe
->STRING	Set $state to STRING and continue ($state can be checked in a case statement after the utility function call)

"""


def expect_arg(action):
	if action.nargs == 0:
		return False
	return True


def is_positional(action):
	# "--foo" before "foo"
	return not action.option_strings


def build_option_string(action):
	# result is in the form ["-f:message:action", "--foo:message:action"]
	# `parts` is the ["-f:", "--foo:"] part
	parts = []
	# `suffix` is the ":message:action" part
	suffix = []

	for option in action.option_strings:
		parts.append(option)

		if expect_arg(action):
			if option.startswith("--"):
				parts[-1] += "="
			elif option.startswith("-"):
				parts[-1] += "+"

		if action.help:
			parts[-1] += f"[{action.help}]"

		if expect_arg(action):
			parts[-1] += ":"

	if not action.option_strings:
		if action.nargs is None:
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
		# not sure what "message"'s purpose is, so we always leave it blank
		if action.choices:
			suffix.append(" :(%s)" % ' '.join(action.choices))  # FIXME escape chars
		elif action.type is int:
			suffix.append(" :_numbers")
		elif action.type:
			suffix.append(f" :{action.type.__name__}")
		else:
			# TODO should suggest "_files" if possible?
			suffix.append(" :")

	return [part + "".join(suffix) for part in parts]


def convert(parser, wrap=True):
	parts = ["_arguments", "-s", "-S"]
	for action in sorted(parser._actions, key=is_positional):
		parts.extend(build_option_string(action))

	parts = [shlex.quote(part) for part in parts]
	if wrap:
		return " \\\n\t".join(parts)
	return " ".join(parts)


class ZshCompletionAction(argparse.Action):
	def __init__(self, option_strings, dest, **kwargs):
		super().__init__(option_strings, dest=argparse.SUPPRESS, nargs=0)

	def __call__(self, parser, namespace, values, option_string=None):
		print(f"#compdef {parser.prog}")
		print(convert(parser))
		parser.exit()


def monkeypatch():
	# force every ArgumentParser.parse_args to have --zsh-completion
	def new_parse_args(self, *args, **kwargs):
		self.add_argument("--zsh-completion", action=ZshCompletionAction)
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
