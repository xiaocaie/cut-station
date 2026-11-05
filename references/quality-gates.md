# 视觉交付的证据与独立审查

本协议适用于 full、preview、edit、font_only 中的视觉阶段。它把制作方提交、程序核验、独立审查与用户验收分开。先读本文件和 [验收标准](../quality-requirements.json)，再完整读取本阶段清单及选定卡片、准确实现；标准的一行摘要不能替代规范全文。

## 1. 什么状态可以记录

| 阶段 | 制作方报告状态 | 门禁计算的出口状态 | 含义 |
| --- | --- | --- | --- |
| motion_sound_plan | submitted | plan_validated | 方案有逐镜头归属、卡片/源码绑定及阅读预算；尚不证明落实 |
| polish | submitted | evidence_ready | 已从当前视频真实取帧，源文件与方案哈希相符；尚不证明美观 |
| review | submitted | independently_reviewed | 当前证据已被另一审查者按标准、逐卡和对应动态主段审查 |
| export | submitted | technical_verified | 当前导出通过容器、参数、PTS/解码，且与被审查视频相同 |
| delivery | submitted | review_ready | 当前授权范围的证据齐备，可交用户验收；不代表用户已接受 |

这些阶段拒绝制作方自填 verified。缺读、缺落实、partial 卡片、无证据、未关闭问题、旧版本证据均不能用“符合要求”文字补过。其他阶段的 verified 仍只是附文件的范围/结构核验记录，不等于整片审美验收。

script、voice_input、voice、subtitles、export-only 与 asset_package 保持原有局部路线。素材包可以只有素材和工程，不为过门禁新增旁白、整片视频或导出。它们的出口不能表述为“整片视觉验收通过”。font_only 仍保护原声音、文本、时长，只需适用的视觉核查，不强制补多卡；full/preview 必须落实至少两种不同卡片并覆盖多个适用主段。无旁白、无字幕合法；有视觉cue时标明实测或视觉/暂定身份。

## 2. 先绑定实际方案

`quality-plan` 接受 schema_version=1 的 JSON。所有路径指向本期实际文件；相对路径按运行目录解释，建议写绝对路径。示意结构如下，真实任务须使用真实卡片、源码和时长：

```json
{
  "schema_version": 1,
  "timeline": "/absolute/project/timeline.json",
  "timing": "/absolute/project/current-cues.json",
  "source_files": ["/absolute/project/Scene.tsx", "/absolute/project/source.mov"],
  "cards": [{
    "id": "selected-card-a",
    "adoption": "implemented",
    "card": "/absolute/skills/selected-card.md",
    "implementation": "/absolute/skills/exact-demo.tsx",
    "code_files": ["/absolute/project/Scene.tsx"],
    "preserved_parameters": "保留的动作、缓动、材质、时长参数",
    "adaptations": "为当前信息和画幅所作的具体改动"
  }],
  "sections": [{
    "id": "main-a",
    "purpose": "观众在本段需要理解的具体任务和结果",
    "shot_ids": ["shot-a"],
    "motion": "library",
    "card_ids": ["selected-card-a"],
    "settled_at": 0.6
  }]
}
```

以上仅展示单条记录，不能作为完整制作的覆盖方案。时间轴为 `{"fps":60,"shots":[{"shot_id":"shot-a","type":"motion_graphic","output_in":0,"output_out":3}]}`。每个镜头归属一个主段，不漏段、不重复归属；实录使用 type=screen_recording，保留 source_in/source_out/output_in/output_out 与 playback_rate=1。卡片必须映射到 source_files 中的本期代码；照搬同一卡片及实现不能冒充多种卡。

实录主段用 `motion=real_recording`，静止阅读用 `motion=static_reading`，两者填写具体 quiet_reason，不填无意义 card_ids。说明静帧用 still=true 并记录 visible_still_label，审查者核对成片标识是否可见。用户明确要求移除该辅助提示时，保留still=true和真实来源身份，使用still_label_override={authority:"user",instruction:"用户明确移除的文字与范围",evidence:"/absolute/project/user-instruction.txt"}；可省略visible_still_label。程序绑定依据文件哈希，独立者核查覆盖范围；不能把普通步骤标题冒充静帧来源标识，也不能把移除提示改成伪造连续操作。该记录仍是代理声明，不认证真实用户身份。settled_at 是成片秒数，落定后至少留0.5秒，复杂信息另做阅读判断。存在显示字幕时 timing 指向有序且不越界的 cues(start/end)；禁字幕时可省略。

完整制作在 motion_sound_plan 登记方案，font_only 在 polish 登记。每张卡和准确实现先 require 进该阶段，再完整 read/ack 全部当前版本块；只返回第一块、读旧版或只记录路径会被拒绝。随后正常 decide/enter/exit，不用登记方案替代阶段出口。

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json require --stage motion_sound_plan --path /absolute/skills/selected-card.md --reason 本期实际采用的完整卡片
# 准确实现也 require，再按 plan 返回的当前块编号 read/ack
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json quality-plan --plan /absolute/project/quality-plan.json --creator-id 本期实际制作方标识
```

## 3. 程序从当前渲染取证

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json quality-evidence --video /absolute/project/current-preview.mp4 --out /absolute/project/quality-evidence-v1
```

输出目录必须全新，不覆盖旧轮。程序实际检查当前视频fps、帧数和时长，解码取首尾、镜头边界/中点、落定前后与每条cue中点，生成带视频/素材/源码/方案/标准哈希的 package.json。输出中的 receipt 给独立审查绑定。失败后不要把残留目录当成功证据；用新目录重试。

这能证明文件未变、帧确实从此视频取得、取证覆盖要求成立，不能证明卡片审美、页面可理解或实际播放。查看真实取帧；动态段另外用实际播放器观察当前视频，不能把自动生成的观察文案当已播放。

## 4. 独立审查当前成片

独立审查者完整读取适用标准与卡/准确实现，查看真实帧，完整动态抽检每个 library 和 real_recording 主段，再写报告。尚未落实或观察不足就记录问题并停止登记通过，交制作方修订。不能仅换 reviewer_id 让同一制作者给自己审批；标识仍为代理声明，本地脚本不认证真实身份。

报告字段：

- reviewer_id：与命令一致，且不同于 creator_id。
- evidence_receipt：当前 package.json 的 receipt。
- criteria：标准文件中所有七项ID，每项 result=pass、具体 observation 和从当前证据包选取的 frames。缺项、重复、unreviewed 或 fail 不能通过。
- card_implementation：每个 library 主段中的每张卡一条 `{section_id,card_id,result:"implemented",observation,frames}`；帧号必须属于本段，具体对照卡片的关键运动/材质/形态，candidate/partial 不能过。
- playback.dynamic_samples：每个动态主段一条 `{section_id,start_frame,end_frame,tool_observation}`，范围完整覆盖该段；end_frame 为不含末帧的边界。不能移用其他段的0–1帧或仅静帧冒充动态观察。
- playback.continuous_visual / continuous_audio：分别填写 observed、not_executed 或 inherited_unchanged。未连续观察可以保持 not_executed，但不得声称已全片连续视听。
- open_findings：明确空数组才可登记通过；有未关闭问题就保留在报告，不提交通过。

若 continuous_visual/audio=observed，另附同名前缀的 `_evidence` 对象，含 start_frame=0、end_frame=全片帧数及 tool_observation。inherited_unchanged 同样须说明范围，另附 inherited_from 原真实观察记录路径、media_path 当前未变的实际媒体路径及 unchanged_files（路径→哈希）。这些媒体须属于当前渲染绑定；视觉继承必须是同一视频，声音继承必须有真实声音流。继承只适用于确实未变的内容，不能用“声音未变”代替观看新画面。

例如动态观察记录：`{"section_id":"main-a","start_frame":0,"end_frame":180,"tool_observation":"本轮播放器观察引用；完整播放0–3秒，具体运动和阅读结果……"}`。这段是字段示意，不是可复用的已观察结论。

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json quality-review --report /absolute/project/independent-review.json --reviewer-id 实际独立审查者标识
```

登记后仍正常退出 review 阶段。独立审查不替代后续技术检查；导出必须是同一被审查视频。交付报告中声明 role=video 的每个产物同样必须与当前被审查视频哈希一致，不能换成另一份参数正确但未审查的成片；没有视频产物的局部/预览/工程交付不因此新增视频要求。换方案、素材/源码、渲染、标准或审查报告使对应旧出口失效；按实际变化 revise 并重新提交，不把旧 verified 搬进 schema_version=3 的状态。

## 5. 交付时的边界

分别报告方案核验、程序取证、独立逐项审查、动态抽检、连续观看、连续听审和真实导出。某项没做就写 pending/not_executed，不用机器取帧或测试通过代替。用户尚未接受时以 review_ready 交付，不填写 user_accepted。

该门禁是 cooperative_local_gate：无法拦截宿主全部工具、阻止恶意手改文件、证明Agent理解或认证身份。它使正常流程中的空声明、缺覆盖与旧证据不能自动放行；审美判断仍由实际看过当前结果的独立审查者负责。
