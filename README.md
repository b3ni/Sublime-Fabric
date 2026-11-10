Sublime Fabric
==============

[Sublime Text](http://www.sublimetext.com/) plugin for running tasks of [Fabric](https://github.com/fabric/fabric). 

Lets run Fabric-Tasks directly from Sublime.

Works with Fabric 2 and 3, and with Fabric 1 (including the `Fabric3` fork).
The version is detected from `fab --version`. Tasks of sub-collections are
listed with their dotted name (`docs.build`).

![Fabric File](http://img52.imageshack.us/img52/2306/readetrabajo1001b.png)

![Execute Tasks](http://img824.imageshack.us/img824/974/readetrabajo1002.png)

Installing
----------
**With the Package Control plugin:** The easiest way to install Sublime Fabric is through Package Control, which can be found at this site: http://wbond.net/sublime_packages/package_control

Once you install Package Control, restart ST and bring up the Command Palette (`Command+Shift+P` on OS X, `Control+Shift+P` on Linux/Windows).

Select "**Fabric: Execute Task**", and a task to execute.

Settings
--------

Open them with "**Preferences: Fabric Settings**" from the Command Palette.

* `fab_path`: the `fab` executable to use. Leave it empty to look for `fab` in a
  virtualenv of the project and otherwise use `fab` from the `PATH`. It can be
  an absolute path (`/usr/local/bin/fab`), a path relative to the first project
  folder (`.venv/bin/fab`) or a bare command name looked up on the `PATH`.
* `search_virtualenv` (default `true`): when `fab_path` is empty, look for
  `fab` in a `.venv`, `venv`, `env` or `.env` folder at the top level of each
  project folder.

If `fab` works in your terminal but not in Sublime Text, Sublime was probably
started with a different `PATH`. Set `fab_path` to the full path printed by
`which fab` (or `where fab` on Windows).

To override a setting for one project, add it with a `fabric_` prefix to the
`settings` section of the `.sublime-project` file:

```json
{
    "settings": {
        "fabric_fab_path": "~/.venvs/deploy/bin/fab"
    }
}
```

Contacts
--------

Sublime Fabric is written by:

* Benito Rodriguez - brarcos@gmail.com

Suggestions, bugs,... https://github.com/b3ni/Sublime-Fabric/issues
