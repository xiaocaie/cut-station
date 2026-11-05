# CutStation · 剪辑站

面向具备本地文件与命令行能力的 AI Agent，按真实素材完成脚本、可选配音、字幕、剪辑包装、预览和导出，也支持只改一个阶段。保护已确认文稿、声音与时间轴，分别记录技术检查和实际观看/听审结果。

这是工作流程 skill 与本地辅助脚本。视频渲染引擎和桌面工具需按实际路线准备；公开包不含公司案例、私人截图、内部文档或用户视频。

## 安装

下载解压或克隆仓库后，在仓库根目录运行（Python 3.9+）：

```bash
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent claude-code
```

其他 Agent 可指定其实际技能目录：

```bash
python3 scripts/install.py --agent generic --dest /absolute/agent/skills
```

安装器会询问是否安装四个推荐项目：HyperFrames、Video Use、Remotion Agent Skills、Video Shotcraft。可全装、选装或跳过；HyperFrames 的三个官方配套入口会提前列出。已存在的目录不会覆盖。选择推荐项才需要 Git 和联网，下载固定版本的 skill 文件，不运行第三方安装钩子或配置账号。

无交互环境默认保留“待用户选择”，不会静默全装。明确跳过用 `--recommended none`，明确全装用 `--recommended all`，选装用 `--recommended remotion,shotcraft`。Agent 必须先取得用户选择才能代填。`--dry-run` 只看计划。

通用 skills 管理器或手动复制不会自动运行本安装器；这种方式安装后，首次调用 skill 时补问依赖。按宿主要求重新扫描/加载。更多见 [安装说明](references/installation.md)。

## 配音提前说明，可直接跳过

需要新旁白时，先说明剪映桌面端整段文本、一次朗读、整轨导出的路线。它需要已安装的应用，以及当前 Agent 的桌面控制工具或用户手动操作；音色、额度和收费条件以账号/版本实际情况为准。

用户可提供已有音频、自己在剪映导出，或完全不要配音。不要配音就不打开剪映、不请求语音服务密钥。字幕可独立跳过；无旁白仍可保留用户同意的音乐和音效。

调用示例：

> 用 cut-station 把这些录屏剪成教程，沿用已有旁白，先交可拖动的预览。

> 用 cut-station 做纯画面演示，不要配音、不要字幕，保留原音乐。

## 兼容性和验证边界

入口采用标准 SKILL.md，脚本不依赖 Codex SDK。其他 Agent 若具备文件、shell、看图/视频与所选渲染能力，可以按同一流程工作。剪映自动化还需该宿主支持桌面控制，不能直接照搬别的宿主 API。

Python 检查通过不等于完整成片通过。当前公开版未完成其他 Agent 的全流程成片对照，不能承诺与 Codex 像素一致或同等审美。见 [兼容性](references/agent-compatibility.md)。

运行测试：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_check.py
```

项目素材/台账放在仓库外。公开上传前执行 [发布检查](references/public-release.md)，并保留字体许可及第三方来源说明。

视觉制作采用 [真实渲染取证与独立审查](references/quality-gates.md)：制作方提交证据，不能自行填写视觉verified；所用镜头卡、动态主段和逐项标准都须落实。程序检查不证明审美或实际听审，review_ready也不代表用户已验收。局部路线不扩展为未经请求的整片或配音。

## 完整钩子库与问题处理

[公开文字库](assets/copywriting/library.json)收录364条句式、96条例子和8类方法，保留来源署名与ID；[选句/填词规则](references/copywriting-library.md)只替换原省略号，用户指定成句则逐字采用。第三方原句不自动适用代码MIT。个人校准和本期项目路径仍不公开。

[问题恢复与工程索引](references/troubleshooting.md)说明字体回落、裁切越界、备注对应、辅助提示局部删除、播放器与导出问题。已证实单次字数限制支持带依据的语义长块配音；未遇上限仍默认整段。视觉门禁拒绝自填verified，绑定当前渲染与独立审查，用户明确删除辅助标识时记录范围和依据。
