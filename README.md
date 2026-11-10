# Sublime Fabric

[![Package Control downloads](https://img.shields.io/packagecontrol/dt/Fabric%20Tasks)](https://packagecontrol.io/packages/Fabric%20Tasks)
[![License: MIT](https://img.shields.io/github/license/b3ni/Sublime-Fabric)](LICENSE)

Run your [Fabric](https://www.fabfile.org/) tasks without leaving
[Sublime Text](https://www.sublimetext.com/).

Sublime Fabric finds the `fabfile.py` files in your project, lists their tasks
in the Command Palette and runs the one you pick, with its output in a new tab.

```
Fabric: Execute Task
  [myproject]: deploy
  [myproject]: show-env
  [myproject]: docs.build-docs
```

## Features

- Lists the tasks of every `fabfile.py` in the open folders, including tasks of
  sub-collections (`docs.build-docs`).
- Works with **Fabric 2 and 3**, and with **Fabric 1** (including the
  `Fabric3` fork). The version is detected from `fab --version`.
- Passes **arguments** to tasks.
- Uses the `fab` of your project's **virtualenv** automatically, or the one you
  choose in the settings.
- Shows the output **while the task runs**. Closing the tab stops the task.
- A fabfile that fails to load doesn't hide the tasks of the others.

## Installation

### Package Control

1. Install [Package Control](https://packagecontrol.io/installation) if you
   don't have it yet.
2. Open the Command Palette (`Ctrl+Shift+P`, or `Cmd+Shift+P` on macOS) and run
   **Package Control: Install Package**.
3. Search for **Fabric Tasks** and install it.

### Manually

Clone the repository into your Packages folder (**Preferences → Browse
Packages…**), in a folder named `Fabric Tasks`:

```sh
git clone https://github.com/b3ni/Sublime-Fabric.git "Fabric Tasks"
```

## Usage

Open the Command Palette and run one of these commands:

| Command | What it does |
|---|---|
| **Fabric: Execute Task** | Lists the tasks of the project and runs the one you pick. |
| **Fabric: Execute Task with Arguments** | Same, then asks for the task's arguments. |
| **Preferences: Fabric Settings** | Opens the default and user settings side by side. |

### Passing arguments

After choosing a task with **Fabric: Execute Task with Arguments**, type its
arguments in the panel. It remembers the last arguments used for each task
until Sublime Text is closed. The syntax depends on your Fabric version:

| Fabric | Syntax | Example |
|---|---|---|
| 2 and 3 | As on the command line, after the task name | `--name=Ana` or `--name "Ana María"` |
| 1 | As after `task:` on the command line | `Ana` or `name=Ana,greeting=hi` |

With Fabric 2 and 3, parameters without a default value can also be given by
position: `Ana`.

### Key binding

The commands have no default key binding. To add one, open **Preferences →
Key Bindings** and add, for example:

```json
{ "keys": ["ctrl+alt+f"], "command": "fab_tasks", "args": {"ask_arguments": true} }
```

Leave out `"args"` to run tasks without asking for arguments.

## Settings

| Setting | Default | Description |
|---|---|---|
| `fab_path` | `""` | The `fab` executable to use. It can be an absolute path (`/usr/local/bin/fab`, `~/.venvs/deploy/bin/fab`), a path relative to the first project folder (`.venv/bin/fab`) or a command name looked up on the `PATH`. |
| `search_virtualenv` | `true` | When `fab_path` is empty, look for `fab` in a `.venv`, `venv`, `env` or `.env` folder at the top level of each project folder. |

When `fab_path` is empty, Sublime Fabric uses the first `fab` it finds in this
order:

1. A virtualenv at the top level of a project folder (if `search_virtualenv`
   is on). A `fab` whose Python interpreter doesn't exist on this machine, for
   example one from a virtualenv created inside a VM, is skipped.
2. `fab` on the `PATH`.

### Per-project settings

To change a setting for one project only, add it with a `fabric_` prefix to the
`settings` section of the `.sublime-project` file:

```json
{
    "folders": [{"path": "."}],
    "settings": {
        "fabric_fab_path": "~/.venvs/deploy/bin/fab"
    }
}
```

## Troubleshooting

**Error `Fabric: could not run "fab"`.** Sublime Text can't find the `fab` executable.
Set `fab_path` to the full path printed by `which fab` (`where fab` on Windows).

**A task works in the terminal but not in Sublime Text.** Sublime Text was
probably started with a different `PATH` (this is common when it's opened from
the macOS Dock or the Windows Start menu) and is running another `fab` or
another Python. Set `fab_path` to the same `fab` you use in the terminal.

**A fabfile is missing from the list.** Its full error is printed in the
Sublime Text console (**View → Show Console**).

## Contributing

Bug reports and suggestions are welcome in the
[issue tracker](https://github.com/b3ni/Sublime-Fabric/issues), and pull
requests too. Thanks to
[everyone who has contributed](https://github.com/b3ni/Sublime-Fabric/graphs/contributors).

## License

[MIT](LICENSE) © Benito Rodríguez Arcos
