# 公众号发文全文高清转换

将 Word（DOCX）中的正文、公式和图片一起转换为可整篇复制到微信公众号的本地 HTML，解决逐个插入公式、公式字号不匹配和图片经中间转换失真的问题。

正文仍是可编辑文字；Word 原生公式批量生成高清 PNG；原 PNG/JPEG 保留文件字节。默认正文 17px、段后 24px、公式 6 倍分辨率，公式按排版尺寸显示。

这是一个“Skill 指令 + 固定程序 + 自动校验”的工具。转换程序不调用大模型 API，不需要 API Key；完成依赖安装后可离线转换。

## 快速安装

Codex、Open Claw 、WorkBuddy、Kimi Work、DouBao都行

直接复制这个链接给你的智能体，并输入“安装这个skill，遇到依赖先检查本地是否安装，若未安装安装适配版本“

```text
安装这个 Skill：https://github.com/kylerrayntan/convert-wechat-article/tree/main/convert-wechat-article
```

也可以将仓库中的整个 `convert-wechat-article/` 子目录复制到智能体的技能目录。支持安装 Skill 的智能体负责自己安装；不能加载 Skill 的工具，可以读取该目录的 `SKILL.md` 并执行其程序。

`agents/openai.yaml` 只提供客户端界面元数据，不参与转换。程序也可直接通过命令行使用。

## 智能体兼容条件

安装 Skill 只是提供指令和程序，首次运行需准备依赖。执行端必须能读取 DOCX、写入输出目录、运行 Python/Node 命令，并能安装锁定的 npm 依赖。纯聊天、不能执行命令或不提供文件访问的客户端不能直接使用。

不绑定某一家模型；是否自动识别 Skill、能否安装依赖及运行脚本，由具体客户端和权限决定。没有逐一验证所有智能体。已有本地验证环境为 macOS；Linux 的 CI 配置需进行运行确认，Windows 尚未验证。含中文的公式还依赖系统可用的中文字形。

## 安装运行依赖

需要 **Python 3.10+** 和 **Node.js 20.9+**。Python 只使用标准库，不需要 `pip install`；建议使用仍受维护的 Node.js LTS 版本。

在仓库根目录运行：

```sh
npm ci --prefix convert-wechat-article --ignore-scripts --no-audit --no-fund
```

- 依赖版本由 `package-lock.json` 锁定；首次安装需要联网，转换时不联网；无需 Word、LibreOffice 或外部图床。

## 使用

安装后对智能体说：

```text
使用 convert-wechat-article，把这份 Word 全文转换为公众号图文。
正文 17px，段后 24px，保留原图，完成自动校验后给我可整体复制的 HTML。
```

或在仓库根目录运行：

```sh
python3 convert-wechat-article/scripts/convert.py '/absolute/article.docx' --output './local-output/article-01'
python3 convert-wechat-article/scripts/verify.py './local-output/article-01'
```

每次转换请指定一个新的输出文件夹，由程序自动创建，避免覆盖旧结果。打开生成的 `article.html`，待图片加载完成，点 **Copy All**，粘贴到公众号正文；等待上传完成，再 **Save as draft** 并通过 **Preview** 查看效果。

详细参数及复制失败处理见 [使用说明](docs/USAGE.md)。

## 适用范围

| 内容   | 当前支持情况                                               |
| ---- | ---------------------------------------------------- |
| 正文   | 按正文段落顺序转换，含空段落、显式粗体/斜体、普通上下标和换行                      |
| 公式   | Word 原生 OMML：横线分数、上下标及组合、普通 box、上下横线、单元素括号等；这些结构可以嵌套 |
| 图片   | 无裁剪、旋转或颜色变换的内嵌 PNG/JPEG，保留文件字节                       |
| 整篇复制 | 文字、公式图片、原图一次复制                                       |

遇到无法转换的内容，程序会提示具体原因。详细说明见 [支持范围](convert-wechat-article/references/supported-inputs.md)。

排版面向公众号统一样式，不复刻 Word 分页和所有字体装饰；第一段按标题处理。输入是 Word 原生公式，不是直接粘贴 LaTeX 的编辑器。

## 仓库结构

```text
README.md
LICENSE
CHANGELOG.md
docs/
tests/run_checks.py
.github/
convert-wechat-article/
  SKILL.md
  LICENSE
  VERSION
  agents/
  assets/
  references/
  scripts/
  tests/
  package.json
  package-lock.json
```

## 数据与隐私

原文档只读，转换在本地完成，不上传到外部图床。生成的文章和报告请按私人资料保管；保留原图也会保留其中已有的 EXIF 等元数据。智能体客户端的数据处理方式由其自身设置决定。详见 [隐私说明](docs/PRIVACY.md)。

## 参与和许可证

反馈问题请提供可公开的最小复现样本，参见 [贡献说明](CONTRIBUTING.md)。项目使用 [MIT License](LICENSE)；第三方依赖遵循各自许可证。
