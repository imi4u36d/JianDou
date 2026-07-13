export interface PromptTemplate {
  id: string;
  title: string;
  tag: string;
  prompt: string;
  imageUrl: string;
}

function templateImage(fileName: string) {
  return `/prompt-templates/${fileName}`;
}

export const promptTemplates: PromptTemplate[] = [
  {
    id: "shojo-manga",
    title: "少女漫画风",
    tag: "大眼 / 网点 / 浪漫",
    imageUrl: templateImage("shojo-manga.webp"),
    prompt: "少女漫画风插画，[主体]，大而闪亮的眼睛，纤细干净线稿，柔和粉紫色调，花瓣和星光背景，细腻网点阴影，高光丰富，浪漫梦幻氛围，竖构图，精致封面感。",
  },
  {
    id: "cyberpunk",
    title: "赛博朋克风",
    tag: "霓虹 / 雨夜 / 高反差",
    imageUrl: templateImage("cyberpunk.webp"),
    prompt: "赛博朋克风格，[主体]，雨夜城市街头，霓虹招牌与蓝紫粉高反差光影，湿润地面反射，未来机械细节，烟雾和电路线缆，电影感低角度，锐利边缘光，高细节。",
  },
  {
    id: "guochao-ink",
    title: "国潮水墨风",
    tag: "留白 / 墨韵 / 东方",
    imageUrl: templateImage("guochao-ink.webp"),
    prompt: "国潮水墨插画，[主体]，宣纸肌理，浓淡墨晕染，大面积留白，金色细线点缀，东方纹样和云气，现代海报构图，克制高级色彩，传统与潮流融合。",
  },
  {
    id: "claymation",
    title: "黏土动画风",
    tag: "手作 / 软质 / 定格",
    imageUrl: templateImage("claymation.webp"),
    prompt: "黏土动画风格，[主体]，手捏黏土材质，圆润比例，轻微指纹和手作瑕疵，柔和棚拍灯光，微缩场景，定格动画质感，温暖可爱，浅景深，真实触感。",
  },
  {
    id: "blind-box-3d",
    title: "软萌 3D 盲盒风",
    tag: "Q版 / 软塑 / 潮玩",
    imageUrl: templateImage("blind-box-3d.webp"),
    prompt: "软萌 3D 盲盒潮玩风，[主体]，Q版大头小身比例，圆润软塑材质，干净棚拍背景，柔和环境光，精致玩具涂装，轻微磨砂质感，治愈可爱，商业级 3D 渲染。",
  },
  {
    id: "pixel-game",
    title: "像素游戏风",
    tag: "复古 / 方块 / 16-bit",
    imageUrl: templateImage("pixel-game.webp"),
    prompt: "复古像素游戏风，[主体]，16-bit pixel art，清晰方块边缘，有限调色板，等距视角，街机游戏氛围，细小高光点，低分辨率颗粒感，画面干净，角色和场景轮廓明确。",
  },
  {
    id: "watercolor-storybook",
    title: "水彩绘本风",
    tag: "纸感 / 透明 / 温柔",
    imageUrl: templateImage("watercolor-storybook.webp"),
    prompt: "水彩绘本风格，[主体]，透明水彩叠色，湿画法边缘，纸张纹理可见，低饱和温柔配色，手绘线条，轻盈留白，童话感构图，温暖自然光，适合插画书页面。",
  },
  {
    id: "y2k-sticker",
    title: "Y2K 闪光贴纸风",
    tag: "镭射 / 可爱 / 高光",
    imageUrl: templateImage("y2k-sticker.webp"),
    prompt: "Y2K 闪光贴纸风，[主体]，镭射渐变，高饱和粉蓝紫配色，果冻质感，粗白描边，星星爱心装饰，闪粉高光，贴纸切边，俏皮网络头像感，干净透明背景感。",
  },
  {
    id: "lofi-low-poly",
    title: "低多边形 3D 风",
    tag: "Lo-fi / 棱面 / 游戏",
    imageUrl: templateImage("lofi-low-poly.webp"),
    prompt: "低多边形 3D 风格，[主体]，low-poly 几何棱面，简化模型，块面材质，柔和单一主光，复古独立游戏画面，轻微颗粒，重点突出轮廓和故事感，不追求过度写实。",
  },
  {
    id: "anime-25d",
    title: "2.5D 动漫渲染",
    tag: "赛璐璐 / 3D / 角色",
    imageUrl: templateImage("anime-25d.webp"),
    prompt: "2.5D 动漫渲染风，[主体]，3D 体积结合赛璐璐上色，清晰黑色轮廓线，非真实感渲染，柔和渐变阴影，发丝和服装层次分明，干净背景，适合虚拟角色头像。",
  },
];
