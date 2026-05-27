# Config Sync

> 一行命令完成服务器配置。定义你的配置文件，跑一个命令，搞定。

基于统一序列的服务器配置同步工具。支持三种操作：**copy**（带 pre/post 钩子的文件复制）、**append**（追加内容到已有文件）、**exe_bash**（执行 shell 脚本）。每一步都是交互式的 —— 替换前你能看到目标文件的当前内容，由你决定是否继续。

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/xiyuanyang-code/ConfigSync.git && cd ConfigSync

# 2. 激活环境并安装依赖
source .venv/bin/activate
uv sync

# 3. 预览同步内容（只读，不做任何修改）
config-sync --dry-run

# 4. 执行完整同步
config-sync
```

## 工作原理

核心思路很简单：在 `config/config.yaml` 中定义一个有序的 `sequence` 步骤列表，然后运行 `config-sync`。每一步是以下三种类型之一：

| 操作 | 作用 | 额外字段 |
|------|------|----------|
| `copy` | 复制 src -> dst（文件或目录） | `pre_install`、`post_check` |
| `append` | 将 src 文件内容追加到 dst 文件 | - |
| `exe_bash` | 执行 shell 命令 | `command` |

对于目录的 `copy` 操作，采用**覆盖合并**策略 —— 只替换 src 中存在的文件，dst 中有但 src 中没有的文件会保留。每次覆盖前，你会看到**目标文件的当前内容**，然后决定是否继续。

所有 bash 命令（`pre_install`、`post_check`、`exe_bash`）会实时输出 stdout/stderr。如果 `pre_install` 失败，你可以选择跳过该步骤。

## 项目结构

```
public/
├── config/
│   └── config.yaml              # 序列定义（编辑这个文件）
├── backup/                      # 待同步的源配置文件
│   ├── .codex/                  #   codex 认证 + 配置
│   ├── .claude/                 #   claude 设置
│   ├── .claude-code-router/     #   router 配置
│   └── .ssh/                    #   ssh 密钥 + 配置
├── scripts/                     # 独立 bash 脚本
│   └── ssh_postcheck.sh
├── src/config_sync/             # 核心 Python 包
│   ├── cli.py                   #   CLI 参数解析
│   ├── sync.py                  #   执行引擎
│   └── utils.py                 #   展示、提示、命令运行
├── pyproject.toml               # 包元数据
├── main.py                      # 旧入口
└── scripts.py                   # 旧入口
```

## 配置说明

编辑 `config/config.yaml`，完整 schema 如下：

```yaml
# 所有相对路径的基准目录，也是 bash 命令的工作目录。
# "." 表示你运行 config-sync 的目录。
work_dir: .

sequence:
  # ── copy: 安装工具 + 同步配置文件 ──
  - action: copy
    name: codex
    src: ./backup/.codex                   # 相对于 work_dir
    dst: ~/.codex                          # 支持 ~ 展开
    pre_install: "which codex || npm install -g @openai/codex"
    post_check: "codex --version"

  - action: copy
    name: claude
    src: ./backup/.claude
    dst: ~/.claude
    pre_install: "npm install -g @anthropic-ai/claude-code"

  - action: copy
    name: ssh_config
    src: ./backup/.ssh
    dst: ~/.ssh
    post_check: "bash scripts/ssh_postcheck.sh"

  # ── append: 向已有文件追加内容 ──
  - action: append
    name: bashrc-extra
    src: ./backup/.bashrc_extra
    dst: ~/.bashrc

  # ── exe_bash: 执行任意命令 ──
  - action: exe_bash
    name: ssh_check
    command: "bash scripts/ssh_postcheck.sh"
```

### 操作类型：`copy`

将文件或目录从 `src` 复制到 `dst`。对于目录，采用**覆盖合并** —— 只处理 src 中的文件，dst 中的其他文件不受影响。

| 字段 | 必填 | 说明 |
|------|------|------|
| `src` | 是 | 源路径（相对于 `work_dir`） |
| `dst` | 是 | 目标路径（支持 `~`） |
| `pre_install` | 否 | 复制**前**执行的 shell 命令 |
| `post_check` | 否 | 复制**后**执行的 shell 命令 |

**生命周期：** `pre_install` -> 展示目标文件当前内容 -> 用户确认 -> 复制 -> `post_check`

### 操作类型：`append`

将 `src` 文件的全部内容追加到 `dst` 文件末尾。如果 `dst` 不存在则创建。

| 字段 | 必填 | 说明 |
|------|------|------|
| `src` | 是 | 源文件路径 |
| `dst` | 是 | 要追加的目标文件 |

### 操作类型：`exe_bash`

以 `work_dir` 为工作目录执行 shell 命令。

| 字段 | 必填 | 说明 |
|------|------|------|
| `command` | 是 | 要执行的 shell 命令 |
| `pre_install` | 否 | 主命令执行前运行的命令 |

## CLI 参考

```
config-sync [选项]

选项：
  -h, --help            显示帮助信息
  --version             显示版本号
  -c, --config CONFIG   指定 config.yaml 路径（默认：config/config.yaml）
  -o, --only NAMES      仅运行指定名称的步骤
  -n, --dry-run         预览变更，不实际写入
  -f, --force           跳过所有确认提示
  -l, --list            以表格形式列出所有序列步骤
```

### 示例

```bash
# 列出所有步骤
config-sync --list

# 仅预览（无副作用）
config-sync --dry-run

# 仅运行 codex 和 claude 步骤
config-sync --only codex claude

# 跳过所有确认提示（谨慎使用！）
config-sync --force

# 使用自定义配置文件
config-sync -c /path/to/custom-config.yaml
```

### 其他入口

```bash
python main.py --dry-run
python -m config_sync --dry-run
```

## 添加自定义步骤

1. 将你的配置文件放到 `backup/` 目录
2. 在 `config/config.yaml` 的 `sequence` 中添加新条目
3. （可选）在 `scripts/` 中添加 `exe_bash` 步骤使用的脚本
4. 运行 `config-sync --dry-run` 预览，然后 `config-sync` 执行
