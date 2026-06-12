# idea-app update

Update tool-managed files in an existing project to the latest templates.

## Usage

```bash
idea-app update [--dry-run] [--force]
```

Run this from inside a project directory that was created by `idea-app init`.

## Options

| Option | Description |
|---|---|
| `--dry-run` | Show what would change without writing anything |
| `--force` | Overwrite all files, including ones you've modified locally |

## How it works

Each tracked file is compared against the manifest hash stored in `pyproject.toml`:

| File state | Action |
|---|---|
| Unchanged since last update | Overwritten with the latest template |
| Locally modified | Skipped; a `.new` file is written alongside for manual review |
| Missing from project | Created |

When files are skipped, you'll see instructions to compare and merge:

```bash
diff app_src/Dockerfile app_src/Dockerfile.new
```

After reviewing, delete the `.new` file and commit the changes.

## Typical workflow

After upgrading `idea-app` to a newer version:

```bash
idea-tools upgrade gds-idea-app-kit
cd gds-idea-app-my-dashboard

# Preview what would change:
idea-app update --dry-run

# Apply changes:
idea-app update

# Review and commit:
git diff
git add -A && git commit -m "Update idea-app managed files"
```

## Which files are managed

See [File ownership](../reference/file-ownership.md) for the complete list of files that `update` manages.
