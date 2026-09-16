# 公众号全文高清转换

将 Word（DOCX）中的**正文、公式和图片一起转换**为可整篇复制到微信公众号的本地 HTML，解决逐个插入公式、公式字号不匹配和图片经中间转换失真的问题。

正文仍是可编辑文字；Word 原生公式批量生成高清 PNG；原 PNG/JPEG 保留文件字节。默认正文 **17px**、段后 **24px**、公式 **6 倍分辨率**，公式按排版尺寸显示。

这是一个“Skill 指令 + 固定程序 + 自动校验”的工具。转换程序不调用大模型 API，不需要 API Key；完成依赖安装后可离线转换。

## 实际验证

- 真实文档：完成含 **138 个公式、3 张原图**的全文转换；用户已在 Safari → 微信公众号的实际流程中确认效果可接受。
- 自动回归：包含 **200 个公式、3 张合成图片**的批量测试、重复输出一致性、内容完整性、异常拒绝和整篇复制载荷测试。
- 自动测试不替代微信端检查；原图字节保留指转换环节，公众号后续处理不受本工具控制。

详见 [验证范围](docs/VALIDATION.md)。

## 快速安装

发布到本仓库后，可向支持安装 GitHub Skill 的智能体发送：

```text
安装这个 Skill：https://github.com/kylerrayntan/convert-wechat-article/tree/main/convert-wechat-article
```

也可以将仓库中的整个 `convert-wechat-article/` 子目录复制到智能体的技能目录。支持安装 Skill 的客户端负责自己的安装流程；不能加载 Skill 的工具，可以读取该目录的 `SKILL.md` 并执行其程序。

`agents/openai.yaml` 只提供客户端界面元数据，不参与转换。程序也可直接通过命令行使用。

## 智能体兼容条件

**不保证所有智能体安装后即可使用。** 安装 Skill 只是提供指令和程序，首次运行仍需准备依赖。执行端必须能读取 DOCX、写入输出目录、运行 Python/Node 命令，并能安装锁定的 npm 依赖。纯聊天、不能执行命令或不提供文件访问的客户端不能直接使用。

程序不绑定某一家模型；是否自动识别 Skill、能否安装依赖及运行脚本，由具体客户端和权限决定。没有逐一验证所有智能体。已有本地验证环境为 macOS；Linux 的 CI 配置需在发布后运行确认，Windows 尚未验证。含中文的公式还依赖系统可用的中文字形。

## 安装运行依赖

需要 **Python 3.10+** 和 **Node.js 20.9+**。Python 只使用标准库，不需要 `pip install`；建议使用仍受维护的 Node.js LTS 版本。

在仓库根目录运行：

```sh
npm ci --prefix convert-wechat-article --ignore-scripts --no-audit --no-fund
```

依赖版本由 `package-lock.json` 锁定。首次安装需要联网，转换时不联网。无需 Word、LibreOffice 或外部图床。

## 使用

对智能体说：

```text
使用 convert-wechat-article，把这份 Word 全文转换为公众号图文。
正文 17px，段后 24px，保留原图，完成自动校验后给我可整体复制的 HTML。
```

或在仓库根目录运行：

```sh
python3 convert-wechat-article/scripts/convert.py '/absolute/article.docx' --output './local-output/article-01'
python3 convert-wechat-article/scripts/verify.py './local-output/article-01'
```

输出目录必须尚不存在。打开生成的 `article.html`，待图片加载完成，点 **Copy All**，粘贴到公众号正文；等待上传完成，再 **Save as draft** 并通过 **Preview** 查看效果。

详细参数及复制失败处理见 [使用说明](docs/USAGE.md)。

## 适用范围

| 内容 | 当前支持情况 |
| --- | --- |
| 正文 | 按正文段落顺序转换，含空段落、显式粗体/斜体、普通上下标和换行 |
| 公式 | Word 原生 OMML：横线分数、上下标及组合、普通 box、上下横线、单元素括号等；这些结构可以嵌套 |
| 图片 | 无裁剪、旋转或颜色变换的内嵌 PNG/JPEG，保留文件字节 |
| 整篇复制 | 文字、公式图片、原图一次复制 |
| 暂未支持 | Word 表格、根号、矩阵、方程组、积分/求和限值，以及其他未适配的文档结构 |

公式是否支持取决于**内部结构**，而非长短或视觉上的复杂程度。遇到不支持的结构会明确失败，不会跳过内容后交付残缺文章。完整边界见 [支持范围](convert-wechat-article/references/supported-inputs.md)。

排版面向公众号统一样式，不复刻 Word 分页和所有字体装饰；第一段按标题处理。输入是 Word 原生公式，不是直接粘贴 LaTeX 的编辑器。

## 仓库结构

```text
README.md
LICENSE
CHANGELOG.md
docs/                         使用、验证和隐私说明
tests/run_checks.py            仓库级测试入口
.github/                      自动测试、问题反馈模板
convert-wechat-article/        可独立安装的 Skill
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

## 自动测试

安装依赖后，在仓库根目录运行：

```sh
python3 tests/run_checks.py
```

测试仅使用程序生成的合成文档，不包含用户资料。GitHub Actions 配置在推送和 Pull Request 时运行；首次发布后的实际结果以 **Actions** 页面为准。

## 数据与联网边界

原文档只读。正文、图片和公式在本机处理；页面不引用外部图床。生成的 HTML、素材和报告可能包含原文及公式，属于你的文章资料，不要当作公开诊断日志上传。

原图文件中的 EXIF/XMP 等元数据也会一并保留，可能含拍摄时间、设备或位置；需要脱敏时请先处理输入图片。本工具不自动清除这些信息，以保持原图字节一致。

本仓库不包含私人测试文档、生成文章、登录凭据或 API Key。公开的 GitHub 用户名和许可证署名属于项目归属信息。智能体本身的数据处理方式由所用客户端决定，本项目只说明转换程序的行为。详见 [隐私与数据说明](docs/PRIVACY.md)。

## 参与和许可证

反馈问题请提供可公开的最小复现样本，参见 [贡献说明](CONTRIBUTING.md)。项目使用 [MIT License](LICENSE)；第三方依赖遵循各自许可证。
