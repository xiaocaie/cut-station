# 内嵌字体与选择

字体随本skill保存在 `assets/fonts/`，不依赖系统曾安装什么。首次使用复制到本期工程的可服务资源目录；打包工程时连同对应OFL许可证复制，不把个人机器绝对路径或外部软链接当永久依赖。文件版本、来源、大小与SHA-256见该目录的 `manifest.json`。

| 字体 | 默认用途 | 文件 |
| --- | --- | --- |
| **得意黑 Smiley Sans** | 首选钩子、大标题、关键词、适合的短字幕；窄斜字形有设计感 | `SmileySans-Oblique.ttf`，网页可选 `SmileySans-Oblique.ttf.woff2` |
| Noto Sans SC | 中文正文、密集信息、需要长时间阅读的字幕和操作说明 | `NotoSansSC-Variable.ttf`，可变字重100–900 |
| Space Grotesk | 英文标题、数字、少量科技感标签；不覆盖中文 | `SpaceGrotesk-Variable.ttf`，可变字重300–700 |

得意黑原字形已倾斜，不额外叠CSS italic/skew。标题优先它，密集正文可选Noto Sans SC；不强求所有字都用展示字体。一片最多三种家族，同级统一，字幕不随每条变化。第三款是可选角色，不要求每片用满三款。

## 实际加载，防止字体回落

网页/Remotion路线将字体复制到 `public/fonts/` 后建立本地 `@font-face`；路径按当前框架资源基准调整。不要仅设置 `font-family: 得意黑` 便声称用到它。

```css
@font-face {
  font-family: "Smiley Sans Local";
  src: url("/fonts/SmileySans-Oblique.ttf.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: block;
}
@font-face {
  font-family: "Noto Sans SC Local";
  src: url("/fonts/NotoSansSC-Variable.ttf") format("truetype");
  font-weight: 100 900;
  font-style: normal;
  font-display: block;
}
@font-face {
  font-family: "Space Grotesk Local";
  src: url("/fonts/SpaceGrotesk-Variable.ttf") format("truetype");
  font-weight: 300 700;
  font-style: normal;
  font-display: block;
}
```

实际渲染前等待所用引擎的字体加载机制完成。验证资源响应成功、`document.fonts.load()`能载入指定字形，并检查最长中文/英文混排、问叹号、数字、标题放大中间帧、字幕边界和手机小图；`document.fonts.check()`本身不证明每个字符都有正确字形。HyperFrames使用本地相对资源或受支持的打包路径，再实查预览，不能假定自动字体服务包含得意黑。

剪映原生字幕若需相同字体，先核对当前UI是否可见并实际选中；需要系统安装时才在本机安装该真实文件，不把“包内有字体”当成剪映已识别。剪映配音不依赖字体安装完成。

## 来源与许可

2026-10-23从以下官方仓库获取，许可证与字体一同内嵌：

- [得意黑官方发布 v2.0.1](https://github.com/atelier-anchor/smiley-sans/releases/tag/v2.0.1)，`SmileySans-OFL.txt`
- [Google Fonts Noto Sans SC](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/notosanssc)，`NotoSansSC-OFL.txt`
- [Google Fonts Space Grotesk](https://github.com/google/fonts/tree/e7db6ca603fd4862010383ff17ffd6cc4ffac1c0/ofl/spacegrotesk)，`SpaceGrotesk-OFL.txt`

三款按SIL Open Font License 1.1随包再分发，保留版权及许可。增加其他字体时也保存官方来源、版本、实际文件和许可；不把来源不明的“免费字体”直接内嵌，不把系统商业字体复制入此包。
