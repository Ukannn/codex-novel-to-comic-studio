# Codex Novel-to-Comic Studio

**面向 Codex 的小说转漫画生产 Skill：把 TXT/EPUB 小说改编成故事优先、可恢复、可审阅、可导出 PDF + CBZ 的漫画项目。**

它不是“一键把书丢给图片模型”。真正的小说改漫画要解决故事拆解、人物动机、因果关系、分镜节奏、对白/旁白/拟声词、角色一致性和章节连贯性。这个 Skill 把 Codex 变成漫画化总编辑：每一步都有文件产物、检查点和审批点，失败后也能从单页或单章恢复。

![原创 demo 成品漫画页](docs/assets/demo-page-001.png)

示例 PDF：[demo-original-one-page.pdf](docs/assets/demo-original-one-page.pdf)

说明：仓库里的 demo 是原创展示图，不来自任何用户上传小说。真实小说源、解析章节、角色卡、成品页、PDF/CBZ 默认被 `.gitignore` 排除，避免误公开版权敏感内容。

## 流程

1. 权利确认：在 `config/user-preferences.json` 选择 `private_experiment`、`licensed_commercial` 或 `public_domain`。
2. 解析输入：支持 `.txt` 和 `.epub`。
3. 读者分析：生成 narrative map、story bible、character/world bible 种子。
4. 视觉 Bible：先生成整页风格预览并确认，再生成核心角色卡/场景卡并确认。
5. 改编计划：生成 `comic-plan.json` 和 `comic-plan.md`。
6. 漫画剧情拆解：生成 `page-story-plan.json`，先把章节讲清楚，再决定页数。
7. 漫画脚本：生成 `page-script.json`，明确必传信息、读者已知/新知/疑问、对白、旁白、SFX 和不可省略因果。
8. 分镜与导演稿：生成 storyboard 和每页 `page-001-director-brief.md`。
9. image2 成品页：默认一页一图，直接生成带画面、分格、对白、旁白、拟声词的 finished page。
10. QC 与修复：按页修复故事、连续性、文字、排版和画面问题。
11. 装订：导出 PDF + CBZ。

## 快速开始

```bash
git clone https://github.com/Ukannn/codex-novel-to-comic-studio.git
cd codex-novel-to-comic-studio
python3 TOOLS/check_state.py .
python3 TOOLS/parse_source.py source/my-book.epub --out source
python3 TOOLS/check_state.py .
```

然后让 Codex 根据 `next_phase` 继续推进，不要覆盖已有阶段产物。

## 配置与工程维护

`config/user-preferences.json` 决定项目的页面尺寸、最低分辨率、裁切规格和目标语言。
生成任务、拼页、规范化、排字和 QC 时显式传入 `--preferences config/user-preferences.json`。
命令行明确指定的宽高或格距优先；未传配置文件的旧命令保留原有默认行为。

```bash
python3 TOOLS/make_image_tasks.py chapters/ch01/storyboard.json --chapter ch01 --preferences config/user-preferences.json
python3 TOOLS/qc_chapter.py chapters/ch01/storyboard.json --finished-pages chapters/ch01/finished-pages --out chapters/ch01/qc-report.json --preferences config/user-preferences.json
python3 -m unittest discover -s tests -v
```

正常的整页生成只需检查 `finished-pages`；检查备用无字底图时再传 `--page-art`。
自动 QC 检查文件和图像，故事、文字和人物一致性仍需按角色规范审阅。

开发环境为 Python 3.10+ 和 `requirements.txt` 中的依赖。开始修改前阅读
[架构与模块所有权](docs/architecture.md)、[架构决策](docs/architecture-decisions.md)、
[治理进度](docs/refactor-progress.md)和[任务池](docs/refactor-backlog.md)。
并行开发使用独立 worktree，先确定文件所有权；CI 自动检查模块依赖、公开接口和行为契约。

## 关键原则

- 故事优先，不硬塞固定页数。
- 默认生成整页 finished page，不默认拆成单格拼接。
- image2 能力强时不要删掉必要对白和剧情信息。
- 风格预览和核心角色卡需要半手动确认。
- 每页必须可追溯来源；新增内容标记 `adaptation_added`。
- 剧情、脚本、导演稿保持串行；导演稿验证通过后，美工 agent 可以按页段并行。
