# 按阶段披露文档与执行协议

本文件是读取、约束台账、阶段门禁、变更失效与完成定义的权威来源。具体制作规则由 [阶段清单](../workflow-manifest.json) 的rule owner指向，默认参数见 [默认档案](default-profile.md)。项目状态写本期工程，不能写进技能安装目录。

## 1 范围和约束

先承接最新对话、已有工程与确认稿。路线：script只写稿、subtitles只做字幕、voice_input仅准备整段配音输入、voice整段配音及字幕、full正式整片、preview仅预览、edit已有片改版、font_only只改字体、export仅导出，asset_package仅素材包。依据本轮实际交付选，不把“完整流程”自动理解成必须发布。原声用existing，无旁白用none；禁止为证明调用技能新增TTS/ASR。

每条用户要求记录 `id / requirement / stages / scope / evidence / supersedes`，保护项按文件/轨道/文本/时间段明确。三条长期硬规始终判断适用范围，只有无相关输出才标不适用并写依据。优先级为最新具体指令→已确认稿件/保护项→技能默认→其他技能通用风格，且服从系统/开发者和真实授权。相冲突的旧要求记录supersedes，不能把某段无音效变成全片永久禁声。

状态：pending / in_progress / verified / blocked / not_applicable。verified必须附实际文件、UI观察、帧号或时间点；未执行不可填通过。用户要求等待审稿时止于对应节点；已有明确继续或全权授权不制造新审批。

## 2 四层披露与完整读取

1. 启动完整读取SKILL、执行协议、默认档案；这是核心包。
2. 本阶段规范在执行前完整读取。清单的sections只选相关完整章节；未指定sections则完整读文件。包含流程、禁止事项、出口与必要子章节，不能只搜“必须”或看标题。
3. 条件资料按实际选用加载：引擎子参考、字体、荧光参考与tokens、选定镜头卡、准确demo、声音设计/美学/授权等。使用前用require登记，再实际读取；同一阶段新增资料使已有规则应用决定失效，重新核对后才能执行。选择引擎时在init使用features中的engine_remotion或engine_hyperframes，或在第一次写/运行引擎代码前require其入口及所需子参考；不能等粗剪完成后才读引擎规范。
4. 历史案例只在相关时读，先看最新状态，旧参数不成为本期常量。

使用 [门禁脚本](../scripts/workflow_guard.py) 的plan列必读包，read每次输出一个不超过约2800字符的完整块。工具响应截断必须补读；每次最多合并少量块，并为实际返回内容保留尾标记，不能在后台遍历文件后直接自动确认。图像块仅列路径，必须另用view_image或允许的图像工具看图再确认。

read产生 `path / source_sha256 / line range / packet id / receipt / END_READ`。实际看到完整块后ack，并附对应工具观察引用；确认当前块END_READ匹配。记录语义是“内容已返回并由Agent确认”，不是证明理解或不可伪造日志。不能先从状态文件取尾标记自动ack，也不能给未实际取得的图像/源码标已读。

同一会话与文档版本的完整读取可跨阶段复用，不每次点击重读。新会话、上下文摘要恢复或无法确认上下文完整时执行resume：当前阶段必读重新返回，仍有效的原产物保留但不能冒称新阶段已读。

## 3 规则应用与三道门

每个阶段用decide建立：**权威规则→本期适用要求→准备采取的动作→验证方法**。素材事实→观众任务→方案选择依据也写入制作记录，不能随机抽钩子/镜头后补一句“符合规范”。

- 进入门：本期范围、前置阶段有效、保护基线未变化。
- 执行门：必读块已完整返回并确认，当前版本规则应用决定齐全。配音必须锁定真实定稿版本；要求先审时记录对应用户确认，不用AI自行批准代替。输入变更后旧锁失效。
- 出口门：操作真实完成、必需验收项有具体证据、产物和保护项通过检查，再进下一依赖阶段。非依赖性的整理可以独立进行，不提前做用户要求等待定稿的配音/画面。

对于本地命令用run，检查失败时实际不执行命令；原生CUA先enter→执行实际操作→提交exit报告。run成功仍不等于出口通过。进入后新增必读资料/规范变化应重新decide和enter。

**当前级别为cooperative_local_gate。** 普通本地脚本无法阻止Agent绕行其他工具、手改台账或伪造观察；read/ack和人工观察属于agent_attested，文件哈希及内置检查是程序计算。全工具不可绕行需要另有隔离的执行器和工具权限控制，本次skill不修改全局权限、不宣称已具备该能力。规则语义、理解、审美、实际听审不能由布尔值或状态JSON证明。

## 4 命令与产物协议

从skill根目录运行以下命令，路径改成真实本期工程位置。先完整读本文件，再用plan/read记录后续阶段资料；已读核心也可通过read补齐可追溯记录。

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json init --mode voice --voice jianying --script-review-required
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json plan --stage intake
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json read --stage intake --chunk 1
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json ack --receipt 本块实际凭据 --end-marker 本块实际尾标记 --observation-ref 本轮真实工具观察引用
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json decide --stage intake --decisions /absolute/project/intake-decisions.json
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json enter --stage intake
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json exit --stage intake --report /absolute/project/intake-report.json
```

init默认不要求用户审稿，仅在用户已经要求时使用该开关。只字幕用subtitles；只改字体用font_only并登记原稿、字幕、声音、时长等保护项，不生成配音或重剪。existing/none的阶段删减来自明确声音路线，不能为了通过门禁随意把应做阶段删成不适用。

规则应用文件为数组，例如：
```json
[{"rule":"SCOPE","action":"本轮只做字体修改，复用当前工程并保护旁白、字幕与时长","verification":"比较保护文件哈希，并检查最长字幕和关键帧的字体加载与遮挡"}]
```

阶段出口报告必须含本阶段清单要求的check ID；每项有verified、具体note、实际证据文件路径，附本阶段产物：
```json
{"stage":"intake","checks":[{"id":"scope_and_protected","status":"verified","note":"已按本轮要求确定只改字体，保护项已与当前文件建立基线","evidence":["/absolute/project/brief.json"]}],"artifacts":[{"path":"/absolute/project/brief.json","role":"file"}]}
```

UI观察可保存截图或真实操作观察文本，注明具体状态、版本、查看范围；文件存在不证明其中叙述属实。报告本身不自动当“看过/听过”证据。程序还会检查证据/产物存在非空、JSON可读、SRT结构、音频/视频元数据与完整解码、整段配音输入来源一致、实测轴有真实声音且不越界，以及声明录屏区间无慢放。语义、真实可见性、冻结/循环伪装、自然停顿与实际审美仍需相应观察。

产物role：voice_input为prepare_voice_text产生的清单；audio为真实主轨；timing为含timing_source=measured、audio_source与cues(start/end)的JSON；srt为最终SRT，可附manifest路径；timeline为内部时间轴JSON；video为实际成片，并在expected中声明预期duration_seconds及本期覆盖规格，门禁实际调用导出检查器核验参数/PTS/解码。只字幕无声音可交provisional，并标身份，不能声称实测。

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json protect --file /absolute/project/旁白.wav
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json lock-script --file /absolute/project/定稿.json --authority user --evidence /absolute/project/对应用户确认记录.txt
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json require --stage motion_sound_plan --path /actual/selected-card.md --reason 本期实际选用的镜头卡
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json run --stage voice_input -- python3 scripts/prepare_voice_text.py /absolute/project/定稿.json /absolute/project/整段配音_v1.txt
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json summary
```

无用户审稿要求且已有全权授权时lock-script可用authority=delegated，evidence保留实际授权与自主冻结依据。脚本不校验这段引用究竟来自用户，Agent不得伪造授权。

## 5 阶段出口与保护

| 阶段 | 必需产物/观察 |
| --- | --- |
| intake | 最新范围、声音路线、交付规格、用户约束、已确认保护项 |
| inventory | 素材元数据/关键操作/结果/源时间、主张证据、缺项；仅主题任务注明事实边界 |
| script | 冻结或待审核身份、正文路线、痛点钩子、承诺兑现、引导与保护项 |
| voice_input | 冻结稿→一个完整TXT→单对象/一次生成清单，哈希一致 |
| jianying_voice | 单文本UI、一次朗读、真实连续音轨及实际导出文件 |
| audio_timing | 最终声音、听审范围、实测句轴；无逐句UI排空和二次变速 |
| srt | 分句/标点/字数/例外、格式检查、时间来源；不把配音用长文本当显示字幕 |
| rough_edit | 同主题语义配对、完整操作与结果、实际录屏时间映射、无慢放 |
| motion_sound_plan | 所选推荐项目分工、选定卡全文/准确源码/声音来源、覆盖及静止区间理由 |
| polish | 真实背景/字体加载、统一荧光、材质/阅读/安全区、特效声音落地 |
| review | 当前预览实际打开、动态/切点/资源检查；连续视听范围分别记录 |
| export | 目标短样、真实容器/规格/帧数/PTS/解码与实际动态检查 |
| delivery | 本轮所有约束逐条关闭，文件/工程/范围/剩余项，保护项不破坏 |

阶段报告和证据/产物保存哈希，后续变化不继续沿用verified。保护基线不能用protect重设来掩盖破坏；明确改动保护范围时保存旧版，记录新用户覆盖与新版本。

## 6 变更与恢复

改稿→受影响配音/字幕/镜头/声音位置重核；删台词→声音/字幕/画面/音效/后续时间同步；只字体→视觉与保护项检查，声音/文本/时长不动；改镜头时长→字幕/SFX/阅读/总长重核。先保存恢复副本与变化原因。

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json revise --from-stage script --reason 用户修改了对应台词与结尾
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json resume
```

revise使该阶段及后续依赖出口失效，不删除真实文件；只重做实际受影响内容。规范哈希变化后原读取/规则决定失效；输入和证据文件变化后旧出口失效。旧台账没有读取凭据时，保留原始证据作为候选，迁移到schema_version=2时从当前阶段所需输入重新核验，不预填已通过，不为建台账盲目重配音。

## 7 验收与回归

运行 `python3 -m unittest discover -s tests -v` 验证：缺读/错尾标记/缺规则决定/前置未完成拦截；先审稿未确认不配音；单文本输入保留标点；分句TTS清单拒绝；保护项改变、规范/输入改变使旧证据失效；错误SRT/无声或坏媒体/录屏0.99倍拒绝；合法局部任务正常继续。测试检查命令是否真实执行、文件变化和退出结果，不能只匹配Agent生成的措辞。

完整成片仍按所用技能要求独立终检；审美、可理解性和实际听感看真实输出。仅文档/脚本回归通过不等于剪映任意长文本、任意音色或整片视听已通过。
