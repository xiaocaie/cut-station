# 素材驱动的动效选型

用户把动效交给 CutStation 判断时，新建 `full`、`preview` 或 `edit` 台账加 `--features adaptive_motion`，与已选引擎特性合用。接续已有项目时运行 `revise --from-stage motion_sound_plan --adaptive-motion --reason '用户本轮要求使用适合的动效'`，保留定稿及其保护记录。只处理文案、字幕、配音、字体或导出时用对应局部路线。用户点名的效果、保护区间、阅读与声音要求按本期指令执行。

## 选型顺序

1. 在粗剪和动效规划中先打开真实素材。按主段标出观众要看懂的页面、操作或结果，记录可用截图的不同页、画幅和关键区，或实录的源时间及连续操作。确定两镜的共同对象和必须给观众读清的内容。用实际截图和可追踪的裁切，避免为凑数量伪造多页。
2. 逐主段分开决定**镜头/转场**和**文字**。从下表和 [MG 动效库](mg-visual-recipes.md) 选镜头，在本页及 [文字动效语法](text-motion-sound-grammar.md) 中选文字。实录连续操作优先保持 1× 和完整结果，可在明确的操作点用 [虚线高亮](green-dashed-highlight.md)。密集正文、表格、关键步骤或定稿保护区域可以停稳、直切或保留原字，记录具体内容和约束。单张图可用简单推进或静止阅读，完整多页序列需要真实不同页面。
3. 符合下表的镜头直接加载相应卡和实现，按当前画幅、时间与字体配置，填入真实素材并在主时间轴调用。使用其他引擎时按同一动作、层级和检查点落实到当前工程，保持单一主时间轴。挑了卡但没有将其写入工程和渲染，只是候选。阅读时长根据画面信息调整，至少满足现有落定门槛。
4. 交付时列出用在哪一段、用到哪项组件和为什么适合，并简要指出值得说明的留静。独立审查对照素材、关键帧和实际播放，确认两类决定都有上下文、采用项做进了当前版本、留静依据成立。

## 组件卡与实拍选型

| 组件 ID | 适合什么素材或镜头 | 动作、验收点 |
| --- | --- | --- |
| `screenshot-wall-sweep` | 有一组可辨认的 PPT、UI 或作品成品截图，开场要先给观众看见整体风格，再切进下一层展台 | 暗场卡墙水平对齐，同宽同高、间距一致，只平移，无逐卡倾斜。需要跨场时，用原槽位的一张真实截图挑起掠过，在前景卡完全遮满画布时切到亮场错层展台。可独立调用平直卡墙；亮场可留在错层陈列后直切。核对槽位接得上、遮满时才换场，轻微透视只施加在前景掠卡及亮场卡片。 |
| `fullscreen-page-gallery` | 至少两张真实的同画幅页面，既要让观众感到作品丰富，也要读到代表页 | 两排背景截图从左往右差速流动，中部单一主卡稳定聚焦。同一首页放大铺满、四角到边、完整停稳后，才横滑切换后续全屏页。新页从左边进，旧页从右侧出，翻页全程相接，背景与边框消失。逐页核对完整性、落定阅读时长和过渡中间帧无空隙。保留可读性要求高的页顺序。 |
| `editorial-titles` | 有明确开场钩子、关键短语或真正的章节层级 | `SemanticHeadline` 用短距遮罩进出，按语义分拍，每拍优先突出一处关键词，字层固定在屏幕中心或安全区，不跟卡墙变形。`NumberedChapter` 用大号序号和短标题，可从错层卡面推到正面全屏。在真素材上检查最宽词组、长标题、字幕避让、字体加载及手机预览。 |

样片用法示例：「使用适合的动效。先扫一眼这些成品截图，把封面推到全屏，再横滑看三个代表页。」先检查代表页画幅和阅读预算，符合时使用全屏横滑组件。若只有一段连续操作的录屏，就核对操作和结果是否应保持实录，按实际 UI 锚点选低干扰强调；开头或章节有独立文字任务时另选文字组件。

## 接入 Remotion

将用到的下列模块及 [showcase-shared.mjs](../assets/effects/showcase-shared.mjs) 复制到工程同一目录。沿用项目的 Remotion 与 React。以下 API 不自带图片、文字、音轨或字体文件。字体由项目实际加载。

- [screenshot-wall.mjs](../assets/effects/screenshot-wall.mjs) 导出 `ScreenshotWallSweep`。传 `sources` 为本期截图 URL 数组。可用 `{src, crop: {scale, origin}}` 给背景素材取局部，例如 `origin: '82% 65%'`。默认平直网格，画面上的钩子放在组件的 children。需要掠过时加 `sweep={{lift: 3.06, cover: 4.12, exit: 4.95}}`，`leadSlot` 选切点可见的墙面槽位；`brightSources`、`brightLayout`（每项 `[x, y, width, roll, yaw, tilt]`，前三项相对画布）和 `brightFront` 可接本期亮场、章节卡。所有时间按当前 Sequence 内的秒数。
- [fullscreen-gallery.mjs](../assets/effects/fullscreen-gallery.mjs) 导出 `FullscreenPageGallery` 和 `gallerySeconds(pageCount, timing)`。传 `pages` 为展示顺序，首项是前景主卡，`tracks` 为两行真实截图数组。全屏页优先导出匹配画幅的原图，先核对裁切安全。共用 `timing` 参数配置推进、阅读、翻页与尾页停留。默认在组件起点后 3.60 秒铺满，4.52 秒才翻第一页，之后每 1.34 秒推进一页，每次横滑 0.38 秒。关键图表按阅读量加时。
- [editorial-titles.mjs](../assets/effects/editorial-titles.mjs) 导出 `SemanticHeadline` 和 `NumberedChapter`。短句用 `beats={[{start: 0.05, end: 1.56, pieces: [{text: '本期成品'}]}]}`；带强调的段落在对应 `piece` 加 `emphasis: true`。按成片语速和屏幕可读性设定间隔。章节传 `number` 与 `title`，需要从卡推满屏时再传 `liftAt`、`landAt`；留出正面稳定阅读。点缀色、底色与字体可按本期视觉方向传入。

```jsx
import {Sequence, staticFile, useVideoConfig} from 'remotion';
import {FullscreenPageGallery, gallerySeconds} from './effects/fullscreen-gallery.mjs';

export function Exhibit() {
  const {fps} = useVideoConfig();
  const pages = ['cover.png', 'overview.png', 'detail.png', 'results.png']
    .map((file) => staticFile(`slides/${file}`));
  const tracks = [[pages[1], pages[3], pages[2]], [pages[2], pages[0], pages[3]]];
  const timing = {hold: 1.1, interval: 1.65};
  return (
    <Sequence durationInFrames={Math.ceil(gallerySeconds(pages.length, timing) * fps)}>
      <FullscreenPageGallery pages={pages} tracks={tracks} {...timing} />
    </Sequence>
  );
}
```

## 质量方案与审查字段

在 [质量方案](quality-gates.md) 的每个 `sections[]` 项中填 `adaptive_motion`。使用实际绝对路径，`material_files` 从本期 `source_files` 引用截图、实录、实际内容依据或已有受保护画面。每类都写可在素材中核对的理由和决定。选用的 `card_ids` 要出现在本段及 `cards[]`，准确实现映射到本期引擎源码。每一张实现卡都要有对应选择，画面和文字可引用共同的组合卡。留静时省略卡 ID、动作起止。动作时间是成片秒数，范围从本段开始到最后一个动作落定；复合镜头仍需给每次展示保留阅读停顿。

```json
{
  "material_files": ["/absolute/project/screens/three-originals.png"],
  "picture": {
    "choice": "use",
    "reason": "同组长宽比一致的原始成品页需要先交代总览，再给观众定位主要成果。",
    "card_ids": ["screenshot-wall-sweep"],
    "start": 0.08,
    "end": 2.2
  },
  "text": {
    "choice": "skip",
    "reason": "原始页面已含需读清的标题和三个数据，覆盖标题会遮住页面中的结论。"
  }
}
```

将卡片和准确实现 `require` 到 `motion_sound_plan`，完整读/确认后登记 `quality-plan`。本页可作为本库的卡片文档，各 ID 对应上面不同的实现文件。工程源码引用共享模块时一并绑定。自动取证在原有镜头边界和落定帧外增加被选动作的首、中、末帧。独立审查 JSON 的 `adaptive_motion` 为每个主段的 `picture`、`text` 各一条 `{section_id, channel, result, observation, frames}`。通过使用 `result="pass"`，正文复核文件和画面支持该决定，帧号取同段证据中的真实帧，选用动作需引用其首、中、末帧。照常填写逐卡实现及动态播放观察。针对动画使用的结构校验和自动取帧不代替实际观看。
