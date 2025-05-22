---
sidebar_position: 2
title: Create Command
description: Create new ElizaOS projects and plugins with an interactive setup process
keywords: [create, project, plugin, setup, scaffolding, initialization, configuration]
image: /img/cli.jpg
---

# Create Command

The `create` command scaffolds new ElizaOS projects or plugins with an interactive setup process.

## Usage

You can use this command in two equivalent ways:

```bash
# Using npm create
npm create eliza [options] [name]

# Using npx directly
npx elizaos create [options] [name]
```

Both commands are functionally identical and support the same options.

## Getting Help

Due to how npm handles flags, there are several ways to get help:

```bash
# Recommended way to view detailed help
npx elizaos create --help

# Quick help overview with npm create
npm create eliza help

# The standard --help flag with npm doesn't work as expected
# as npm intercepts it and shows npm's own help
```

## Options

| Option              | Description                                     |
| ------------------- | ----------------------------------------------- |
| `-d, --dir <dir>`   | Installation directory (default: `.`)           |
| `-y, --yes`         | Skip confirmation (default: `false`)            |
| `-t, --type <type>` | Type of template to use (`project` or `plugin`) |
| `[name]`            | Name for the project or plugin (optional)       |

## Directory Handling

When using npm create, the tool intelligently detects paths and directory names:

```bash
# All these commands create a project in the specified directory:

# With -d flag (explicit)
npm create eliza -d ./my-dir

# With path-like arguments (auto-detected)
npm create eliza ./my-dir

# With regular directory names (also auto-detected)
npm create eliza my-project-dir

# With plugin type and directory
npm create eliza plugin ./plugins-dir/my-plugin
npm create eliza plugin my-plugin-dir
```

The CLI automatically treats arguments as directory paths unless they are recognized keywords like "plugin" or "project".

## Project Types

### Project

Creates a standard ElizaOS project with agent configuration and knowledge setup.

```bash
# Using npm create
npm create eliza -t project

# Using npx
npx elizaos create -t project
```

Project structure:

```
my-agent-project/
├── knowledge/          # Knowledge files for RAG
├── src/                # Source code directory
├── package.json
└── other configuration files
```

### Plugin

Creates a plugin that extends ElizaOS functionality.

```bash
# Using npm create
npm create eliza -t plugin

# Using npx
npx elizaos create -t plugin

# Shorthand syntax - only with npm create
npm create eliza plugin my-plugin-name
```

Plugin structure:

```
my-plugin/
├── src/                # Plugin source code
├── package.json
└── other configuration files
```

## Interactive Process

The command launches an interactive wizard when run without all options:

1. **Project Type**: Select between project or plugin
2. **Project Name**: Enter a name for your project/plugin
3. **Database Selection**: Choose database (PGLite or Postgres)
4. **Database Configuration**: Configure Postgres if selected

## Examples

### Creating a basic project

```bash
# Using npm create
npm create eliza

# Using npx
npx elizaos create
# Then follow the interactive prompts
```

### Creating a plugin

```bash
# Using npm create
npm create eliza -t plugin
# Or with shorthand syntax
npm create eliza plugin my-plugin-name

# Using npx
npx elizaos create -t plugin
# Then follow the interactive prompts
```

### Specifying a directory

```bash
# Using npm create (standard flag format)
npm create eliza -d ./my-projects/new-agent

# Using npm create (path auto-detection)
npm create eliza ./my-projects/new-agent

# Using npm create with plugin type
npm create eliza plugin ./my-projects/my-plugin

# Using npx
npx elizaos create --dir ./my-projects/new-agent
```

### Skipping confirmation prompts

```bash
# Using npm create
npm create eliza -y

# Using npx
npx elizaos create --yes
```

## Next Steps

After creation, see the [Getting Started](../quickstart.md) for next steps.

## Related Commands

- [`start`](./start.md): Start your created project
- [`dev`](./dev.md): Run your project in development mode
- [`env`](./env.md): Configure environment variables
