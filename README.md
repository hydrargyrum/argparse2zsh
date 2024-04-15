# argparse2zsh

argparse2zsh generates zsh completion for a command that uses Python's [`argparse`](https://docs.python.org/3/library/argparse.html) system.

## How to run it

It can be run both as a single-shot app, or as a permanent library:

- single-shot generate zsh completion for a python command, without requiring any modification to python code
- permanently add a `--zsh-completion` flag to the command, by incorporating argparse2zsh in the app

### single shot run

In this example, we assume:

- `~/.zsh/functions/` dir is in `$fpath`
- `foo` is the command for which completions should be generated

```sh
argparse2zsh.py foo --zsh-completion > ~/.zsh/functions/_foo
```

argparse2zsh runs `foo --zsh-completion` and dynamically injects a `--zsh-completion` flag into it (in memory only, it's a temporary runtime modification).
This flag outputs a completion script for zsh on stdout.
This completions script is output in the right location so zsh can find it next.

Then, pressing tab key after typing `foo ` will complete its options or arguments.

### permanently add a `--zsh-completion`

argparse2zsh is under WTFPL lincense so you can just drop the file in the repository of your app, then

```
from .argparse2zsh import ZshCompletionAction
```

and

```
parser = ArgumentParser()  # just like before
...
parser.add_argument("--zsh-completion", action=ZshCompletionAction)  # add this line
```

## Caveats

### argparse2zsh is agnostic of the app

Zsh completion scripts are quite powerful and can complete files, hostnames, and a lot more things.
However, argparse2zsh only bases itself on how an app uses `argparse`, and it rarely holds such level of details.
So argparse2zsh cannot guess everything that would make a completion script completely adapted to the app.
It is able to list positional arguments and optional args in the form of `--<NAME>` or `-<LETTER>` and use their help message.
It will also indicate that zsh file completion should be used for arguments named `--file` or stuff like this, but it can't do much better.

In short, argparse2zsh can only adhere to the `argparse` description, not to the app.

However, it's possible to fine-tune the generated completion script manually, argparse2zsh generating most of the completion structure as a base.

### argparse2zsh CLI tool runs the app

argparse2zsh does not do static analysis of the wrapped app source code to determine the arguments.
It really runs it and tries to exit as soon as `argparse.parse_args` is run.
This means the app will do everything before argument parsing, whatever it is.
Fortunately, most apps often do argument parsing at the start of the app, and don't clobber any data before, or don't even try to read any configuration files before, so it's often not a problem.

## How it works

argparse2zsh monkeypatches `ArgumentParser.parse_args` to inject its own `argparse.Action`.
In it, it will introspect the current parser being used to explore all options and convert them to zsh syntax.
