import argparse


def test_assumptions():
	parser = argparse.ArgumentParser()

	# basic
	assert parser._positionals in parser._action_groups
	assert parser._optionals in parser._action_groups

	# option
	action = parser.add_argument("--qux")
	assert action in parser._actions
	assert action in parser._optionals._group_actions

	# argument group
	group = parser.add_argument_group()
	assert group._actions is parser._actions
	assert group in parser._action_groups
	action = group.add_argument("--foo")
	assert group._group_actions == [action]
	assert action in parser._actions

	# exclusive arg group
	group = parser.add_mutually_exclusive_group()
	assert group._actions is parser._actions
	assert group not in parser._action_groups
	action = group.add_argument("--bar")
	assert group._group_actions == [action]
	assert action in parser._actions

	# subparsers
	subs = parser.add_subparsers()
	assert subs in parser._subparsers._group_actions
	sub = subs.add_parser("baz")
	assert subs.choices["baz"] is sub
	action = sub.add_argument("--baz")
	assert action in sub._actions
	assert action not in parser._actions

	from IPython import embed
	embed()


if __name__ == "__main__":
	test_assumptions()
