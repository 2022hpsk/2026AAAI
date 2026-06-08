/* SpeakerMem-R1 进度汇报 slides 生成器 */
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa");

// ---------- palette ----------
const C = {
  dark:   "12183A", dark2: "1C2550", navy: "27347A",
  ink:    "1E293B", ink2: "334155", muted: "64748B", faint: "94A3B8",
  white:  "FFFFFF", panel: "F1F5F9", panel2: "F8FAFC", line: "E2E8F0",
  cyan:   "0EA5C4", cyanDk: "0E7490", cyanBg: "E0F4F9",
  amber:  "E08A1E", amberDk: "B45309", amberBg: "FBEFD9",
  green:  "0E9F6E", greenBg: "E1F5EC",
  red:    "DC4A52", redBg: "FBE6E7",
  violet: "6D5BD0", violetBg: "ECE9FB",
};
const F = { head: "Microsoft YaHei", body: "Microsoft YaHei", num: "Arial Black" };
const W = 10, H = 5.625, M = 0.5, TOTAL = 29;
const RECT = "rect", ROUND = "roundRect", OVAL = "ellipse", LINE = "line";
const mkShadow = (o={}) => ({ type:"outer", color: o.color||"0F172A", blur:o.blur||8, offset:o.offset||3, angle:135, opacity:o.opacity||0.12 });

// ---------- icons ----------
const iconCache = {};
async function icon(Comp, hex) {
  const key = (Comp.name||"x") + hex;
  if (iconCache[key]) return iconCache[key];
  const svg = RDS.renderToStaticMarkup(React.createElement(Comp, { color: "#"+hex, size: "256" }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  const data = "image/png;base64," + png.toString("base64");
  iconCache[key] = data;
  return data;
}

async function main() {
  const pres = new pptxgen();
  pres.defineLayout({ name: "W", width: W, height: H });
  pres.layout = "W";
  pres.author = "SpeakerMem-R1";
  pres.title = "SpeakerMem-R1 研究进度汇报";

  const IC = {};
  const need = [
    ["users", FA.FaUsers], ["brain", FA.FaBrain], ["robot", FA.FaRobot],
    ["check", FA.FaCheckCircle], ["times", FA.FaTimesCircle], ["warn", FA.FaExclamationTriangle],
    ["book", FA.FaBookOpen], ["db", FA.FaDatabase], ["layers", FA.FaLayerGroup],
    ["scale", FA.FaBalanceScale], ["diagram", FA.FaProjectDiagram], ["flask", FA.FaFlask],
    ["code", FA.FaCode], ["file", FA.FaFileAlt], ["route", FA.FaRoute],
    ["flag", FA.FaFlagCheckered], ["q", FA.FaRegQuestionCircle], ["chart", FA.FaChartBar],
    ["shield", FA.FaShieldAlt], ["clock", FA.FaRegClock], ["target", FA.FaBullseye],
    ["comments", FA.FaComments], ["grad", FA.FaGraduationCap], ["med", FA.FaStethoscope],
    ["build", FA.FaBuilding], ["arrow", FA.FaArrowRight], ["bulb", FA.FaLightbulb],
    ["search", FA.FaSearch], ["bolt", FA.FaBolt], ["star", FA.FaStar],
  ];
  for (const [k, Comp] of need) {
    IC[k] = {};
    for (const col of [C.cyan, C.amber, C.green, C.red, C.violet, C.navy, C.white, C.muted, C.faint, C.cyanDk, C.amberDk])
      IC[k][col] = await icon(Comp, col);
  }

  // ---------- helpers ----------
  let PG = 1; // title = page 1; footer() advances and stamps the page number (auto, order = display order)
  function footer(s) {
    PG++;
    s.addText("SpeakerMem-R1  ·  研究进度汇报  ·  2026-06-02", { x:M, y:H-0.34, w:6, h:0.26, fontSize:8, color:C.faint, fontFace:F.body, margin:0, valign:"middle" });
    s.addText(`${PG} / ${TOTAL}`, { x:W-1.2, y:H-0.34, w:0.7, h:0.26, fontSize:8, color:C.faint, align:"right", fontFace:F.body, margin:0, valign:"middle" });
  }
  function header(s, kicker, title, accent=C.cyan) {
    s.addShape(RECT, { x:M, y:0.44, w:0.15, h:0.15, fill:{color:accent} });
    s.addText(kicker, { x:M+0.25, y:0.37, w:W-2*M-0.25, h:0.3, fontSize:11, color:accent, bold:true, charSpacing:1, fontFace:F.body, margin:0, valign:"middle" });
    s.addText(title, { x:M, y:0.74, w:W-2*M, h:0.62, fontSize:24, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
  }
  function card(s, x, y, w, h, opt={}) {
    const { fill=C.white, accent=null, shadow=true, lineCol=C.line } = opt;
    s.addShape(RECT, { x, y, w, h, fill:{color:fill}, line: lineCol?{color:lineCol, width:0.75}:{type:"none"}, shadow: shadow?mkShadow():undefined });
    if (accent) s.addShape(RECT, { x, y, w:0.06, h, fill:{color:accent} });
  }
  function pill(s, x, y, w, h, text, opt={}) {
    const { bg=C.cyanBg, fg=C.cyanDk, fs=9.5, bold=true } = opt;
    s.addShape(ROUND, { x, y, w, h, fill:{color:bg}, line:{type:"none"}, rectRadius:Math.min(h/2,0.12) });
    s.addText(text, { x, y, w, h, fontSize:fs, color:fg, bold, align:"center", valign:"middle", fontFace:F.body, margin:0 });
  }
  function iconChip(s, x, y, d, iconData, opt={}) {
    const { bg=C.cyanBg, pad=0.18 } = opt;
    s.addShape(OVAL, { x, y, w:d, h:d, fill:{color:bg}, line:{type:"none"} });
    s.addImage({ data:iconData, x:x+pad, y:y+pad, w:d-2*pad, h:d-2*pad });
  }

  // =================================================================
  // SLIDE 1 — Title
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.dark };
    s.addShape(RECT, { x:0, y:0, w:0.18, h:H, fill:{color:C.cyan} });
    s.addShape(OVAL, { x:8.0, y:-1.4, w:3.6, h:3.6, fill:{color:C.navy, transparency:55}, line:{type:"none"} });
    s.addShape(OVAL, { x:9.0, y:3.9, w:2.6, h:2.6, fill:{color:C.cyanDk, transparency:65}, line:{type:"none"} });

    s.addText("AAAI 2027 投稿  ·  面向多方对话记忆的强化学习", { x:0.85, y:0.7, w:8.5, h:0.3, fontSize:12.5, color:C.cyan, bold:true, charSpacing:1, fontFace:F.body, margin:0 });
    s.addText("SpeakerMem-R1", { x:0.8, y:1.12, w:8.8, h:1.0, fontSize:52, bold:true, color:C.white, fontFace:F.head, margin:0, valign:"middle" });
    s.addText("研究进度汇报", { x:0.85, y:2.2, w:8.5, h:0.5, fontSize:22, color:"CBD5E1", fontFace:F.head, margin:0 });
    s.addText("首个面向多方对话（3+ 人 / 群聊）记忆管理的强化学习框架", { x:0.85, y:2.8, w:8.6, h:0.4, fontSize:14.5, color:"93A4C9", fontFace:F.body, margin:0 });

    const my = 3.6;
    const spk = [["A", C.cyan], ["B", C.amber], ["C", C.violet]];
    spk.forEach((sp, i) => {
      const cx = 1.0 + i*0.62;
      s.addShape(OVAL, { x:cx, y:my, w:0.46, h:0.46, fill:{color:sp[1]}, line:{color:C.dark, width:1.5} });
      s.addText(sp[0], { x:cx, y:my, w:0.46, h:0.46, fontSize:13, bold:true, color:C.dark, align:"center", valign:"middle", fontFace:F.num, margin:0 });
    });
    s.addImage({ data: IC.arrow[C.faint], x:2.66, y:my+0.1, w:0.3, h:0.26 });
    s.addShape(ROUND, { x:3.14, y:my-0.12, w:3.0, h:0.72, fill:{color:C.dark2}, line:{color:C.cyanDk, width:1}, rectRadius:0.08 });
    s.addImage({ data: IC.layers[C.cyan], x:3.32, y:my+0.06, w:0.36, h:0.36 });
    s.addText("5 层 Speaker-Indexed Memory", { x:3.76, y:my-0.12, w:2.32, h:0.72, fontSize:11, bold:true, color:"DDE6F5", valign:"middle", fontFace:F.body, margin:0 });

    s.addShape(LINE, { x:0.85, y:4.8, w:8.3, h:0, line:{color:"31407A", width:1} });
    const metas = [["汇报人", "（学生）"], ["日期", "2026-06-02"], ["目标会议", "AAAI 2027 · 蒙特利尔"]];
    metas.forEach((mm, i) => {
      const mx = 0.85 + i*2.9;
      s.addText(mm[0], { x:mx, y:4.94, w:2.7, h:0.24, fontSize:9.5, color:C.cyan, bold:true, fontFace:F.body, margin:0 });
      s.addText(mm[1], { x:mx, y:5.18, w:2.7, h:0.26, fontSize:12, color:"CBD5E1", fontFace:F.body, margin:0 });
    });
  }

  // =================================================================
  // SLIDE 2 — TL;DR
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "一页摘要 · 给导师快速过目", "纸面准备已完成，实验是唯一硬缺口", C.cyan);

    const lx = M, lw = 5.55, ty = 1.55, ch = 1.06, gap = 0.18;
    const cards = [
      { ic:"check", col:C.green, bg:C.greenBg, t:"已完成 · 纸面准备", b:"系统性文献调研 35 篇 · 方法设计 · 7 章论文草稿 · 6 个代码模块（dry-run / mock 测试通过）" },
      { ic:"target", col:C.cyan, bg:C.cyanBg, t:"已确认 · 零篇先例的研究空白", b:"「多方 + 说话人锚定 + RL 训练」三者交集，截至 2026/6/2 无人涉足（4 轮检索验证）" },
      { ic:"warn", col:C.red, bg:C.redBg, t:"唯一硬缺口 · 实验零开工", b:"真实实验一项都还没跑（无训练数据、无算力投入）—— 论文里所有实验数字都是占位符" },
    ];
    cards.forEach((cd, i) => {
      const y = ty + i*(ch+gap);
      card(s, lx, y, lw, ch, { accent:cd.col });
      iconChip(s, lx+0.2, y+0.2, 0.66, IC[cd.ic][cd.col], { bg:cd.bg, pad:0.17 });
      s.addText(cd.t, { x:lx+1.02, y:y+0.13, w:lw-1.2, h:0.32, fontSize:13.5, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
      s.addText(cd.b, { x:lx+1.02, y:y+0.45, w:lw-1.22, h:0.5, fontSize:10.5, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.05 });
    });

    const rx = 6.35, rw = W-M-rx, rh = ch*3+gap*2;
    card(s, rx, ty, rw, rh, { fill:C.dark, shadow:true, lineCol:null });
    s.addImage({ data: IC.q[C.amber], x:rx+0.26, y:ty+0.26, w:0.4, h:0.4 });
    s.addText("最需导师指点的 3 件事", { x:rx+0.78, y:ty+0.24, w:rw-0.95, h:0.44, fontSize:14, bold:true, color:C.white, fontFace:F.head, margin:0, valign:"middle" });
    s.addShape(LINE, { x:rx+0.26, y:ty+0.82, w:rw-0.52, h:0, line:{color:"33407A", width:1} });
    const items = [
      ["时间线决策", "冲刺 AAAI 2027（约 7 周，风险高）还是放更晚会议做扎实？"],
      ["算力与经费", "约 4×A100 / ~$1,100 训练 + ~$50–100 数据 API，是否可行？"],
      ["数据策略", "三个 benchmark 都无训练集，须全合成 —— 质量能否撑 RL？"],
    ];
    items.forEach((it, i) => {
      const y = ty + 1.02 + i*0.78;
      s.addShape(OVAL, { x:rx+0.26, y:y, w:0.34, h:0.34, fill:{color:C.amber}, line:{type:"none"} });
      s.addText(String(i+1), { x:rx+0.26, y:y, w:0.34, h:0.34, fontSize:13, bold:true, color:C.dark, align:"center", valign:"middle", fontFace:F.num, margin:0 });
      s.addText(it[0], { x:rx+0.72, y:y-0.04, w:rw-0.95, h:0.28, fontSize:12, bold:true, color:C.amber, fontFace:F.head, margin:0, valign:"middle" });
      s.addText(it[1], { x:rx+0.72, y:y+0.235, w:rw-0.95, h:0.5, fontSize:9.5, color:"C7D0E8", fontFace:F.body, margin:0, lineSpacingMultiple:1.02 });
    });
    footer(s, 2);
  }

  // =================================================================
  // SLIDE 3 — Significance
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "研究定位与意义 · Significance", "群聊 AI 的刚需，且现有系统集体失败", C.cyan);

    card(s, M, 1.5, W-2*M, 0.72, { fill:C.dark, shadow:true, lineCol:null });
    s.addImage({ data: IC.bulb[C.amber], x:M+0.24, y:1.66, w:0.4, h:0.4 });
    s.addText([
      { text:"一句话定位：", options:{ bold:true, color:C.amber } },
      { text:"SpeakerMem-R1 是首个用于多方对话（3+ 人）记忆管理的强化学习框架。", options:{ color:C.white } },
    ], { x:M+0.78, y:1.5, w:W-2*M-1.0, h:0.72, fontSize:13.5, fontFace:F.head, margin:0, valign:"middle" });

    const sy = 2.5;
    s.addText("真实场景大量存在", { x:M, y:sy, w:4.5, h:0.26, fontSize:11, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const sc = [
      ["build", "企业群聊", "Slack / 飞书 / Teams\n数十人共享频道"],
      ["grad", "在线教育", "一师多生\n跟踪学生理解"],
      ["med", "会诊 / 剧本杀", "多来源信息\n须区分说话人"],
    ];
    const scw = (4.85-2*0.2)/3;
    sc.forEach((c, i) => {
      const x = M + i*(scw+0.2), y = sy+0.34, h=1.62;
      card(s, x, y, scw, h, { fill:C.panel2 });
      iconChip(s, x+(scw-0.62)/2, y+0.18, 0.62, IC[c[0]][C.cyanDk], { bg:C.cyanBg, pad:0.16 });
      s.addText(c[1], { x:x, y:y+0.86, w:scw, h:0.3, fontSize:11.5, bold:true, color:C.ink, align:"center", fontFace:F.head, margin:0 });
      s.addText(c[2], { x:x+0.05, y:y+1.14, w:scw-0.1, h:0.44, fontSize:8.8, color:C.muted, align:"center", fontFace:F.body, margin:0, lineSpacingMultiple:1.0 });
    });

    const hx = 5.55, hw = W-M-hx;
    s.addText("硬数据：现有系统几乎「没有记忆」", { x:hx, y:sy, w:hw, h:0.26, fontSize:11, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const stats = [
      [ "0.12–0.18", "SocialMemBench", "最好的开源记忆系统（Mem0 / LangMem / Graphiti / Cognee）在多方社交场景的准确率", C.red ],
      [ "46%", "GroupMemBench", "最强系统上限；连朴素 BM25 都能追平 —— 瓶颈是结构性缺陷，非模型不聪明", C.amber ],
    ];
    stats.forEach((st, i) => {
      const y = sy+0.34 + i*0.84, h=0.74;
      card(s, hx, y, hw, h, { accent:st[3] });
      s.addText(st[0], { x:hx+0.18, y:y, w:1.55, h:h, fontSize:26, bold:true, color:st[3], align:"left", valign:"middle", fontFace:F.num, margin:0 });
      s.addText(st[1], { x:hx+1.8, y:y+0.07, w:hw-1.98, h:0.24, fontSize:10.5, bold:true, color:C.ink, fontFace:F.head, margin:0 });
      s.addText(st[2], { x:hx+1.8, y:y+0.3, w:hw-1.98, h:0.42, fontSize:8.5, color:C.muted, fontFace:F.body, margin:0, lineSpacingMultiple:1.0 });
    });
    footer(s, 3);
  }

  // =================================================================
  // SLIDE 4 — Gap
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "研究空白 · Gap（4 轮检索验证）", "多方 × RL 记忆 = 零篇先例", C.amber);

    card(s, M, 1.5, W-2*M, 1.06, { fill:C.dark, shadow:true, lineCol:null });
    const cw = (W-2*M-0.95)/2;
    s.addText([
      { text:"现有 RL 记忆方法\n", options:{ bold:true, color:C.cyan, fontSize:12.5, breakLine:true } },
      { text:"全是 dyadic（一对一 user–assistant）", options:{ color:"DDE6F5", fontSize:11 } },
    ], { x:M+0.3, y:1.6, w:cw, h:0.86, valign:"middle", fontFace:F.body, margin:0, align:"center", lineSpacingMultiple:1.15 });
    s.addText([
      { text:"现有多方对话记忆工作\n", options:{ bold:true, color:C.amber, fontSize:12.5, breakLine:true } },
      { text:"全是 training-free / 仅做评测", options:{ color:"DDE6F5", fontSize:11 } },
    ], { x:M+0.65+cw, y:1.6, w:cw, h:0.86, valign:"middle", fontFace:F.body, margin:0, align:"center", lineSpacingMultiple:1.15 });
    s.addShape(OVAL, { x:W/2-0.45, y:1.74, w:0.9, h:0.58, fill:{color:C.amber}, line:{color:C.dark, width:2.5} });
    s.addText("交集=0", { x:W/2-0.45, y:1.74, w:0.9, h:0.58, fontSize:12, bold:true, color:C.dark, align:"center", valign:"middle", fontFace:F.head, margin:0 });

    s.addText("三个「说话人盲区」结构性缺陷 —— 不是调参能解决的", { x:M, y:2.78, w:W-2*M, h:0.3, fontSize:12, bold:true, color:C.ink, fontFace:F.head, margin:0 });

    const defs = [
      ["users", "Action space 缺 speaker_id", "把多方发言强行合并成「user」，存储时就丢失了「这是谁的信息」。"],
      ["scale", "Reward 的 speaker 盲区", "Levenshtein 只比对整体记忆：Alice 的事存到 Bob 名下，内容对、归属错，仍得高分。"],
      ["diagram", "Credit assignment 盲区", "不同 rollout 面对的说话人分布不同，奖励本质不可比 —— LoGo 也无法保证公平。"],
    ];
    const dw = (W-2*M-2*0.28)/3;
    defs.forEach((d, i) => {
      const x = M + i*(dw+0.28), y=3.18, h=1.72;
      card(s, x, y, dw, h, { accent:C.amber, fill:C.amberBg, lineCol:null });
      iconChip(s, x+0.22, y+0.22, 0.6, IC[d[0]][C.amberDk], { bg:C.white, pad:0.15 });
      s.addText(String(i+1), { x:x+dw-0.62, y:y+0.16, w:0.42, h:0.42, fontSize:20, bold:true, color:"E9C99A", align:"right", fontFace:F.num, margin:0 });
      s.addText(d[1], { x:x+0.22, y:y+0.92, w:dw-0.4, h:0.34, fontSize:11.5, bold:true, color:C.amberDk, fontFace:F.head, margin:0 });
      s.addText(d[2], { x:x+0.22, y:y+1.26, w:dw-0.42, h:0.42, fontSize:9, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.02 });
    });
    footer(s, 4);
  }

  // =================================================================
  // SLIDE 5 — Literature
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "文献调研 · 共 35 篇，均 10KB+ 中文详解", "锁定 3 个对比锚点，确认零篇空白", C.cyan);

    const lx=M, lw=2.85, ly=1.55, lh=3.3;
    card(s, lx, ly, lw, lh, { fill:C.dark, shadow:true, lineCol:null });
    s.addText("35", { x:lx, y:ly+0.18, w:lw, h:0.95, fontSize:58, bold:true, color:C.cyan, align:"center", valign:"middle", fontFace:F.num, margin:0 });
    s.addText("篇 · 覆盖 5 大主题", { x:lx, y:ly+1.14, w:lw, h:0.3, fontSize:12, bold:true, color:C.white, align:"center", fontFace:F.head, margin:0 });
    s.addShape(LINE, { x:lx+0.3, y:ly+1.56, w:lw-0.6, h:0, line:{color:"33407A", width:1} });
    const groups = ["RL 记忆方法 + 竞品", "多方对话记忆系统", "Benchmark 数据集", "长程信用分配", "安全 / 隐私视角"];
    groups.forEach((g, i) => {
      const y = ly+1.62 + i*0.33;
      s.addShape(OVAL, { x:lx+0.3, y:y+0.09, w:0.1, h:0.1, fill:{color:C.cyan}, line:{type:"none"} });
      s.addText(g, { x:lx+0.52, y:y, w:lw-0.74, h:0.28, fontSize:10.5, color:"C7D0E8", fontFace:F.body, margin:0, valign:"middle" });
    });

    const rx=lx+lw+0.3, rw=W-M-rx;
    s.addText([
      { text:"★ ", options:{ color:C.amber, bold:true } },
      { text:"三大贡献分别「扩展」自这三篇 2026 最新 dyadic 工作 —— 差异清晰、可对比", options:{ color:C.muted } },
    ], { x:rx, y:ly-0.02, w:rw, h:0.26, fontSize:10, bold:true, fontFace:F.body, margin:0 });
    const anc = [
      ["DeltaMem", "2026.04", "Memory-based Levenshtein 稠密过程奖励", "① SpeakerLevenshtein", C.cyan],
      ["Memory-R2", "2026.05", "LoGo-GRPO 恢复公平比较 + 渐进课程", "② SC-LoGo-GRPO", C.violet],
      ["CoMAM", "2026.03", "joint 端到端多 agent RL，自适应 credit", "joint training 思路", C.amber],
    ];
    anc.forEach((a, i) => {
      const y = ly+0.34 + i*0.86, h=0.74;
      card(s, rx, y, rw, h, { accent:a[4] });
      s.addText(a[0], { x:rx+0.22, y:y+0.08, w:1.7, h:0.3, fontSize:14, bold:true, color:C.ink, fontFace:F.head, margin:0 });
      pill(s, rx+1.78, y+0.13, 0.78, 0.24, a[1], { bg:C.panel, fg:C.muted, fs:8.5 });
      s.addText(a[2], { x:rx+0.22, y:y+0.42, w:rw-2.55, h:0.28, fontSize:8.8, color:C.muted, fontFace:F.body, margin:0 });
      s.addImage({ data: IC.arrow[a[4]], x:rx+rw-2.5, y:y+0.28, w:0.22, h:0.2 });
      s.addText(a[3], { x:rx+rw-2.22, y:y, w:2.05, h:h, fontSize:10.5, bold:true, color:a[4], valign:"middle", fontFace:F.head, margin:0, align:"left" });
    });
    card(s, rx, ly+2.98, rw, 0.32, { fill:C.amberBg, shadow:false, lineCol:null });
    s.addText([
      { text:"关键结论：", options:{ bold:true, color:C.amberDk } },
      { text:"三个竞品均无公开代码 → baseline 须自复现，但 reviewer 也更难质疑。", options:{ color:C.ink2 } },
    ], { x:rx+0.16, y:ly+2.98, w:rw-0.3, h:0.32, fontSize:9.5, fontFace:F.body, margin:0, valign:"middle" });
    footer(s, 5);
  }

  // =================================================================
  // SLIDE 6 — Related Work expand A: Dyadic RL lineage
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "Related Work 展开 ① · Dyadic RL 记忆", "RL 记忆方法谱系：一年快速演进，但全在 dyadic", C.cyan);

    const Hd = (t)=>({ text:t, options:{ fill:{color:C.dark}, color:C.white, bold:true, fontSize:9.5, align:"center", valign:"middle", fontFace:F.head } });
    const cl = (t,o={})=>({ text:t, options:{ fontSize:8.7, color:o.color||C.ink2, align:o.align||"left", valign:"middle", fontFace:F.body, bold:o.bold||false, fill:{color:o.fill||C.white} } });
    const st = C.amberBg;
    const rows = [
      [Hd("方法"), Hd("时间"), Hd("核心技术"), Hd("关键结果")],
      [cl("Memory-R1",{bold:true,color:C.ink}), cl("2025.08",{align:"center"}), cl("首个 RL 记忆 · 双 agent（Manager+Answer）+ Memory Distillation"), cl("152 条训练，LoCoMo F1 +48%")],
      [cl("AgeMem",{bold:true,color:C.ink,fill:C.panel2}), cl("2026.01",{align:"center",fill:C.panel2}), cl("step-wise GRPO · 6 类工具动作统一 LTM/STM",{fill:C.panel2}), cl("5 benchmark +4.8–8.6%",{fill:C.panel2})],
      [cl("Mem-α",{bold:true,color:C.ink}), cl("2026.01",{align:"center"}), cl("core / episodic / semantic 三组件架构"), cl("30k 训练泛化到 400k+ token")],
      [cl("MEM1 / MemSearcher",{bold:true,color:C.ink,fill:C.panel2}), cl("2025",{align:"center",fill:C.panel2}), cl("masked trajectory · multi-context GRPO",{fill:C.panel2}), cl("3B 模型超过 7B baseline",{fill:C.panel2})],
      [cl("Mem-T",{bold:true,color:C.ink}), cl("2026.01",{align:"center"}), cl("Memory Operation Tree（MoT-GRPO）+ hindsight credit"), cl("比 Mem0 / A-MEM +14.9%")],
      [cl("DeltaMem  ★",{bold:true,color:C.cyanDk,fill:st}), cl("2026.04",{align:"center",fill:st}), cl("Memory-based Levenshtein 稠密过程奖励",{fill:st}), cl("R = 0.1 fmt + 0.1 ret + 0.8 state",{fill:st,color:C.ink})],
      [cl("Memory-R2  ★",{bold:true,color:C.violet,fill:st}), cl("2026.05",{align:"center",fill:st}), cl("LoGo-GRPO（local rerollout）+ 渐进课程 8→32",{fill:st}), cl("修复信用分配不公",{fill:st,color:C.ink})],
      [cl("CoMAM  ★",{bold:true,color:C.amberDk,fill:st}), cl("2026.03",{align:"center",fill:st}), cl("joint 端到端 RL + rank-consistency 自适应 credit",{fill:st}), cl("PersonaMem +8.5–16.7%",{fill:st,color:C.ink})],
    ];
    s.addTable(rows, { x:M, y:1.48, w:W-2*M, colW:[1.7, 0.8, 4.05, 2.45], rowH:[0.3,0.33,0.33,0.33,0.33,0.33,0.33,0.33,0.33], border:{type:"solid", color:C.line, pt:0.5}, valign:"middle", margin:[1,4,1,4], autoPage:false });

    card(s, M, 4.56, W-2*M, 0.44, { fill:C.amberBg, accent:C.amber, lineCol:null });
    s.addText([
      { text:"全部 dyadic（两人对话）", options:{ bold:true, color:C.amberDk } },
      { text:" —— 无一考虑说话人归属与受众适配。 ★ = 我们三大贡献的直接前身（另有 MemBuilder 归因稠密奖励、R²-Mem F1 +22.6% 同属 dyadic）。", options:{ color:C.ink2 } },
    ], { x:M+0.18, y:4.56, w:W-2*M-0.34, h:0.44, fontSize:9, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDE 7 — Related Work expand: training-free / single-user memory landscape
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "Related Work 展开 · 通用记忆系统全景", "从「基线三件套」到 2026 新秀 —— 全是单用户 / dyadic", C.cyan);

    // Group A: classic three
    s.addText("① 经典三件套 · training-free 基线", { x:M, y:1.5, w:W-2*M, h:0.26, fontSize:10.5, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const ga = [
      ["Mem0", "LLM 驱动 CRUD（ADD/UPDATE/DELETE）· production 标准"],
      ["A-MEM", "原子记忆 + 动态链接（无预定义 schema）"],
      ["MemoryBank", "艾宾浩斯遗忘曲线（强度衰减）"],
    ];
    const aw = (W-2*M-2*0.28)/3;
    ga.forEach((g, i) => {
      const x = M + i*(aw+0.28), y=1.78, h=0.96;
      card(s, x, y, aw, h, { accent:C.cyan });
      s.addText(g[0], { x:x+0.18, y:y+0.12, w:aw-0.32, h:0.28, fontSize:12.5, bold:true, color:C.cyanDk, fontFace:F.head, margin:0 });
      s.addText(g[1], { x:x+0.18, y:y+0.42, w:aw-0.34, h:0.46, fontSize:8.5, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.06 });
    });

    // Group B: 2025-26 newcomers
    s.addText("② 2025–26 新秀（更强，但仍单用户）", { x:M, y:2.9, w:W-2*M, h:0.26, fontSize:10.5, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const gb = [
      ["MemoryOS", "EMNLP'25", "OS 式短/中/长期分层；LoCoMo F1 +49%", C.violet],
      ["MemGAS", "ICLR'26", "多粒度关联 + GMM 聚类 + 熵路由检索", C.amber],
      ["LightMem", "ICLR'26", "在线/离线分离 + 压缩；token 降至 1/117", C.green],
      ["GAM", "RL · 读侧", "Memorizer + Researcher 双 LLM · JIT 检索", C.cyanDk],
    ];
    const bw = (W-2*M-3*0.22)/4;
    gb.forEach((g, i) => {
      const x = M + i*(bw+0.22), y=3.18, h=1.0;
      card(s, x, y, bw, h, { accent:g[3] });
      s.addText(g[0], { x:x+0.14, y:y+0.1, w:bw-0.26, h:0.26, fontSize:11.5, bold:true, color:g[3], fontFace:F.head, margin:0 });
      pill(s, x+0.14, y+0.38, bw-0.28, 0.22, g[1], { bg:C.panel, fg:C.muted, fs:7.5 });
      s.addText(g[2], { x:x+0.14, y:y+0.62, w:bw-0.26, h:0.34, fontSize:7.6, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.04 });
    });

    // punchline banner
    card(s, M, 4.42, W-2*M, 0.5, { fill:C.amberBg, accent:C.amber, lineCol:null });
    s.addText([
      { text:"全部 single-user / dyadic", options:{ bold:true, color:C.amberDk } },
      { text:" —— 连 2026 最新系统都不绑定说话人。这是 DeferMem 等论文的标准对照集（我们须覆盖）；而多方场景下 BM25 即可追平它们 → 正是我们 speaker-grounded 的缺口。", options:{ color:C.ink2 } },
    ], { x:M+0.18, y:4.42, w:W-2*M-0.34, h:0.5, fontSize:9, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.04 });
    footer(s);
  }

  // =================================================================
  // SLIDE 8 — Related Work expand B: multi-party systems + credit assignment
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "Related Work 展开 ② · 多方系统 & 信用分配", "多方记忆系统：要么 training-free，要么只做生成", C.cyan);

    const lx=M, lw=5.7, ly=1.55;
    s.addText("多方对话记忆系统（无一可学习记忆读写）", { x:lx, y:ly, w:lw, h:0.26, fontSize:10.5, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const sysm = [
      ["Collaborative Mem", "共享/私有记忆 + bipartite 访问控制 + provenance", "写入是固定规则，不可学习"],
      ["G-Memory", "三层图记忆（insight/query/interaction），+20.89%", "training-free；面向 AI-agent 非人类群聊"],
      ["SHARE / MOOM", "从电影剧本构造含共享记忆的多说话人数据集", "数据构造可借鉴，非方法"],
      ["SA-LLM", "说话人感知对比学习", "针对对话生成，非记忆管理"],
      ["MuPaS", "role-masked SFT 训练多方对话模型", "我们直接借用 role-mask 做 Stage 1"],
    ];
    sysm.forEach((sy, i) => {
      const y = ly+0.32 + i*0.63, h=0.54;
      card(s, lx, y, lw, h, { accent:C.cyan });
      s.addText(sy[0], { x:lx+0.18, y:y+0.05, w:1.78, h:0.44, fontSize:10, bold:true, color:C.ink, valign:"middle", fontFace:F.head, margin:0 });
      s.addText(sy[1], { x:lx+1.96, y:y+0.05, w:lw-2.12, h:0.24, fontSize:8.4, color:C.ink2, fontFace:F.body, margin:0, valign:"middle" });
      s.addText([{ text:"局限：", options:{ color:C.red, bold:true } }, { text:sy[2], options:{ color:C.muted } }], { x:lx+1.96, y:y+0.28, w:lw-2.12, h:0.24, fontSize:8, fontFace:F.body, margin:0, valign:"middle" });
    });

    const rx=lx+lw+0.3, rw=W-M-rx, ry=1.55;
    card(s, rx, ry, rw, 3.36, { fill:C.dark, shadow:true, lineCol:null });
    s.addText("长程信用分配工具箱", { x:rx+0.24, y:ry+0.2, w:rw-0.4, h:0.3, fontSize:12.5, bold:true, color:C.white, fontFace:F.head, margin:0 });
    const tools = [
      ["GRPO", "group-relative 优势；长程难分关键步"],
      ["HiPER", "分层 RL + HAE；ALFWorld 97.4%"],
      ["HCAPO", "LLM 作 post-hoc critic 做 hindsight 归因"],
    ];
    tools.forEach((t, i) => {
      const y = ry+0.62 + i*0.5;
      s.addShape(OVAL, { x:rx+0.24, y:y+0.04, w:0.12, h:0.12, fill:{color:C.cyan}, line:{type:"none"} });
      s.addText(t[0], { x:rx+0.44, y:y-0.04, w:rw-0.6, h:0.24, fontSize:10.5, bold:true, color:C.cyan, fontFace:F.head, margin:0 });
      s.addText(t[1], { x:rx+0.44, y:y+0.19, w:rw-0.64, h:0.26, fontSize:8.3, color:"C7D0E8", fontFace:F.body, margin:0 });
    });
    s.addShape(LINE, { x:rx+0.24, y:ry+2.22, w:rw-0.48, h:0, line:{color:"33407A", width:1} });
    s.addText([
      { text:"均在单一用户视角。", options:{ bold:true, color:C.amber } },
      { text:"多方需在 操作 × 说话人 双维度精化信用分配 —— 正是 SC-LoGo 的切入点。", options:{ color:"D7DEEF" } },
    ], { x:rx+0.24, y:ry+2.34, w:rw-0.46, h:0.62, fontSize:9, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.08 });
    s.addText([
      { text:"交集仍空白：", options:{ bold:true, color:C.cyan } },
      { text:"多方 + 说话人锚定 + RL 记忆管理 = 零篇先例。", options:{ color:C.white } },
    ], { x:rx+0.24, y:ry+2.96, w:rw-0.46, h:0.36, fontSize:9.2, bold:true, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDE 8 — Datasets
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "数据集调研 · 主战场全部 2026 年新出", "三个多方 benchmark 都没有训练集", C.amber);

    const head = (t) => ({ text:t, options:{ fill:{color:C.dark}, color:C.white, bold:true, fontSize:10.5, align:"center", valign:"middle", fontFace:F.head } });
    const cell = (t, o={}) => ({ text:t, options:{ fontSize:9.5, color:o.color||C.ink2, align:o.align||"left", valign:"middle", fontFace:F.body, bold:o.bold||false, fill:o.fill?{color:o.fill}:{color:C.white} } });
    const rows = [
      [head("多方 Benchmark"), head("时间"), head("规模 / 特点"), head("关键基准数字")],
      [cell("GroupMemBench", {bold:true, color:C.ink}), cell("2026.05",{align:"center"}), cell("图驱动合成多方对话"), cell("最强系统仅 46%；BM25 追平神经系统", {color:C.red, bold:true})],
      [cell("EverMemBench", {bold:true, color:C.ink, fill:C.panel2}), cell("2026.02",{align:"center", fill:C.panel2}), cell("每实例 1M+ token，2,400 QA", {fill:C.panel2}), cell("Oracle 多跳归因仅 ~26%", {color:C.red, bold:true, fill:C.panel2})],
      [cell("SocialMemBench", {bold:true, color:C.ink}), cell("2026.05",{align:"center"}), cell("430 personas / 1,031 QA / 348 sessions"), cell("开源框架 0.12–0.18；目标超 0.35", {color:C.red, bold:true})],
    ];
    s.addTable(rows, { x:M, y:1.52, w:W-2*M, colW:[2.0, 0.9, 3.05, 3.05], rowH:[0.34, 0.5, 0.5, 0.5], border:{type:"solid", color:C.line, pt:0.75}, valign:"middle", margin:[2,5,2,5], autoPage:false });

    s.addText([
      { text:"dyadic 对照（证明 N=1 时方法不退化）：", options:{ bold:true, color:C.ink2 } },
      { text:"  LOCOMO  ·  LongMemEval  ·  PersonaMem-v2", options:{ color:C.muted } },
    ], { x:M, y:3.48, w:W-2*M, h:0.28, fontSize:9.5, italic:true, fontFace:F.body, margin:0 });

    card(s, M, 3.86, W-2*M, 1.04, { fill:C.amberBg, accent:C.amber, lineCol:null });
    s.addImage({ data: IC.warn[C.amberDk], x:M+0.24, y:4.08, w:0.5, h:0.5 });
    s.addText("关键发现：训练数据必须完全合成", { x:M+0.92, y:3.98, w:W-2*M-1.1, h:0.32, fontSize:13, bold:true, color:C.amberDk, fontFace:F.head, margin:0 });
    s.addText("三者均为纯评测集，即便有对话也只有 QA pairs、没有 memory 操作序列标注（每 turn 该 WRITE / UPDATE / DELETE 哪条）。已设计图驱动合成 pipeline（GroupMemBench graph-grounded + Memory-R1 的 152 条拐点思路），目标先合成 200 条（50×4 场景）。", { x:M+0.92, y:4.3, w:W-2*M-1.12, h:0.56, fontSize:9.5, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.02 });
    footer(s, 6);
  }

  // =================================================================
  // SLIDE 9 — Method expand: problem formalization + action space
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 · 问题形式化", "多方记忆的 3 个新挑战 + 说话人归属动作空间", C.cyan);

    card(s, M, 1.48, W-2*M, 0.5, { fill:C.panel2, shadow:false });
    s.addText([
      { text:"形式化：", options:{ bold:true, color:C.cyanDk } },
      { text:"对话 C = {(s_t, u_t)}，K 个说话人；查询 q =（提问者 s_ask, 目标 s_target, 问题文本）。Agent 维护说话人索引记忆 M 并检索作答。", options:{ color:C.ink2 } },
    ], { x:M+0.18, y:1.48, w:W-2*M-0.34, h:0.5, fontSize:9.8, fontFace:F.body, margin:0, valign:"middle" });

    const ch = [
      ["users", "① 说话人归属", "每条事实须带来源：f =（content, s_owner）。多说话人讨论同一实体时，归属模糊。", "dyadic 下 owner 永远是唯一对方"],
      ["comments", "② 受众适配", "作答需考虑提问者 s_ask 的视角、其与 s_target 的关系、以及访问权限。", "回答因人而异"],
      ["shield", "③ 跨说话人隐私", "s_i 拥有的信息可能不应被 s_j 访问 → 记忆须具备显式访问控制。", "新增评测维度"],
    ];
    const cw = (W-2*M-2*0.28)/3;
    ch.forEach((c, i) => {
      const x = M + i*(cw+0.28), y=2.16, h=1.6;
      card(s, x, y, cw, h, { accent:C.cyan, fill:C.cyanBg, lineCol:null });
      iconChip(s, x+0.2, y+0.2, 0.56, IC[c[0]][C.cyanDk], { bg:C.white, pad:0.14 });
      s.addText(c[1], { x:x+0.18, y:y+0.84, w:cw-0.36, h:0.3, fontSize:12, bold:true, color:C.cyanDk, fontFace:F.head, margin:0 });
      s.addText(c[2], { x:x+0.18, y:y+1.14, w:cw-0.36, h:0.46, fontSize:8.7, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.02 });
    });

    card(s, M, 3.98, W-2*M, 0.94, { accent:C.amber, fill:C.amberBg, lineCol:null });
    s.addText("说话人归属动作空间（扩展自 AgeMem，强制说话人元数据）", { x:M+0.2, y:4.04, w:W-2*M-0.4, h:0.26, fontSize:10.5, bold:true, color:C.amberDk, fontFace:F.head, margin:0 });
    s.addText("A = { WRITE(c, s, A, l) · UPDATE(e, c) · DELETE(e) · SUMMARY(E, l) · PROMOTE(e) · SUPPRESS(e, λ) · READ(s, s′) · NOOP }", { x:M+0.2, y:4.33, w:W-2*M-0.4, h:0.28, fontSize:9.2, color:C.ink, fontFace:"Consolas", margin:0, valign:"middle" });
    s.addText([
      { text:"关键区别：", options:{ bold:true, color:C.amberDk } },
      { text:"每个 WRITE 强制带 speaker owner s + 受众集合 A —— dyadic 动作空间（Memory-R1 / DeltaMem）没有这层条件化，下游奖励函数也就无从谈起。", options:{ color:C.ink2 } },
    ], { x:M+0.2, y:4.6, w:W-2*M-0.4, h:0.28, fontSize:8.7, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDE 10 — Method: system data flow + core capability
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 · 系统数据流", "对话 → 记忆 → 检索 → 回答：精准区分『谁说了什么』", C.cyan);

    card(s, M, 1.48, W-2*M, 0.82, { fill:C.dark, shadow:true, lineCol:null });
    s.addImage({ data: IC.bulb[C.amber], x:M+0.24, y:1.68, w:0.42, h:0.42 });
    s.addText([
      { text:"核心能力：", options:{ bold:true, color:C.amber } },
      { text:"在多角色（3+ 人）对话中精准区分『谁说了什么』—— 把不同说话人的事实 / 观点 / 答案分得清清楚楚，回答时准确归属到正确的人、时间、语境。受众适配与隐私只是其中一项子能力。", options:{ color:"DDE6F5" } },
    ], { x:M+0.82, y:1.48, w:W-2*M-1.05, h:0.82, fontSize:10.5, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.08 });

    const boxes = [
      [C.cyan,   "A_mem 写记忆", "输入 新发言 u_t + 记忆摘要", "输出 记忆动作 WRITE/UPDATE…"],
      [C.violet, "M 记忆 · 5 层", "按说话人分桶存储", "per-speaker×3 + group×2"],
      [C.amber,  "A_ret 检索",   "输入 查询 q + 可访问记忆", "输出 相关片段 context"],
      [C.green,  "A_ans 回答",   "输入 q + context", "输出 答案 a"],
    ];
    const bw=1.95, gap=0.37, by=2.82, bh=1.6;
    boxes.forEach((b, i) => {
      const x = M + i*(bw+gap);
      card(s, x, by, bw, bh, { shadow:true });
      s.addShape(RECT, { x, y:by, w:bw, h:0.4, fill:{color:b[0]} });
      s.addText(b[1], { x:x+0.14, y:by, w:bw-0.26, h:0.4, fontSize:10.5, bold:true, color:C.white, valign:"middle", fontFace:F.head, margin:0 });
      s.addText(b[2], { x:x+0.14, y:by+0.56, w:bw-0.26, h:0.4, fontSize:8, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.05 });
      s.addText(b[3], { x:x+0.14, y:by+1.04, w:bw-0.26, h:0.4, fontSize:8, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.05 });
      if (i < 3) s.addImage({ data: IC.arrow[C.faint], x:x+bw+0.04, y:by+0.66, w:0.29, h:0.26 });
    });

    card(s, M, 4.56, W-2*M, 0.42, { fill:C.cyanBg, accent:C.cyan, lineCol:null });
    s.addText([
      { text:"一个模型扮三个角色", options:{ bold:true, color:C.cyanDk } },
      { text:"（A_mem / A_ret / A_ans 共享 backbone）；A_mem 逐轮在线写入，A_ret / A_ans 在查询 q 到来时运行。", options:{ color:C.ink2 } },
    ], { x:M+0.18, y:4.56, w:W-2*M-0.34, h:0.42, fontSize:9.2, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDES 11–16 — Method: 6 detailed who-said-what example slides (one per page)
  // =================================================================
  {
    const EXAMPLES = [
      {
        type: "单流混淆", title: "多人同主题，归属不能混", accent: C.cyan,
        scene: "企业项目群（Slack / Teams / 飞书）· 团队分工",
        chat: [
          { n:"Alice", t:"模型训练我来负责" },
          { n:"Bob", t:"数据清洗交给我" },
          { n:"Carol", t:"我盯评测和指标" },
          { n:"Dave", t:"前端和 demo 归我" },
        ],
        qa: [ { q:"谁负责评测？", a:"Carol" }, { q:"Bob 做什么？", a:"数据清洗" } ],
        difficulty: "现有系统把多人发言压成一条「user」记忆，分工糊成一团 —— 问「谁做评测」只能猜或张冠李戴。GroupMemBench 上这类归属错误占比最高。",
        solution: "动作空间强制 speaker_id + per_speaker_core 分层存 + SpeakerLevenshtein 按说话人分桶奖励 —— 每条事实硬锚定到人。",
        domains: ["企业协作","会议纪要","项目管理","多 agent 协作"],
      },
      {
        type: "跨说话人引用", title: "记住「谁说的」和「说的是谁」", accent: C.violet,
        scene: "客服 / CRM、合规审计、法律取证（provenance 是硬需求）",
        chat: [
          { n:"Alice", t:"Bob 上次提过，他想从测试转去做开发" },
          { n:"Dave", t:"哦？他不是一直做测试吗" },
        ],
        qa: [ { q:"Bob 想转岗吗？", a:"是（Alice 转述）" }, { q:"这条谁说的？", a:"来源 = Alice" } ],
        difficulty: "信息主体是 Bob、来源是 Alice。现有系统要么把它记成 Alice 的事，要么丢掉来源 —— 合规 / 审计必须保留「谁说的」。",
        solution: "每条 entry 同时存 speaker_id（来源）与 content（主体）+ links 关联两个说话人；READ_CROSS 带访问控制。",
        domains: ["客服 / CRM","合规审计","法律取证","多 agent 溯源"],
      },
      {
        type: "同类实体不合并", title: "大群组里，同类实体不能错并", accent: C.amber,
        scene: "医疗多学科会诊 / 在线教育（一师多生）",
        chat: [
          { n:"张医生", t:"我这位患者血糖偏高" },
          { n:"李医生", t:"我接的是术后感染" },
          { n:"王医生", t:"我的患者心率不齐" },
        ],
        qa: [ { q:"李医生的患者什么情况？", a:"术后感染" } ],
        difficulty: "多人都在谈「我的患者 / 我的症状」，同类实体极易被合并成一团；规模越大越糊。EverMemBench 上 Oracle 多跳归因仅约 26%。",
        solution: "唯一 s_owner + per-speaker 分层，从结构上禁止跨人 merge；worst-speaker bonus 不放过最难归属的人。",
        domains: ["医疗会诊","在线教育","多用户助手","大型社群"],
      },
      {
        type: "冲突信念按人分", title: "各持己见，按人记住不同立场", accent: C.green,
        scene: "决策 / 评审会议、multi-agent 辩论",
        chat: [
          { n:"Alice", t:"这版我主张上 PyTorch" },
          { n:"Bob", t:"我坚持 JAX，编译更快" },
          { n:"Carol", t:"我都行，听大家的" },
        ],
        qa: [ { q:"Bob 倾向哪个？", a:"JAX" }, { q:"谁主张 PyTorch？", a:"Alice" } ],
        difficulty: "同一议题各人观点冲突，现有系统常取「最后一条」或合并成单一结论，丢掉「谁持什么立场」。决策复盘 / 多 agent 协作必须保留分歧。",
        solution: "per-speaker 各记一份信念，UPDATE 不覆盖他人；检索时按 speaker 返回各自立场。",
        domains: ["决策会议","评审 / 投票","multi-agent","舆情 / 民调"],
      },
      {
        type: "per-speaker 时序", title: "每个人的状态，各有时间线", accent: C.cyanDk,
        scene: "长期陪伴 / 心理咨询、销售 CRM、健康随访",
        chat: [
          { n:"Alice", t:"（第 3 天）我在 A 公司做后端" },
          { n:"Alice", t:"（第 20 天）跳槽去 B 公司了，转做算法" },
        ],
        qa: [ { q:"Alice 现在在哪？", a:"B 公司做算法" }, { q:"她之前呢？", a:"A 公司后端" } ],
        difficulty: "每个说话人的事实独立演化。现有系统 UPDATE 多是 destructive 覆盖，丢掉历史；问「现在 / 之前」答不全。",
        solution: "per_speaker_episodic 时间索引层 + 非破坏性 UPDATE + PROMOTE（反复出现 → 核心），保留可追溯演化。",
        domains: ["陪伴 / 心理咨询","销售 CRM","健康随访","长期个人助理"],
      },
      {
        type: "群体 vs 个体 + 隐私", title: "分清「群里共识」与「个人偏好」，并按人保密", accent: C.red,
        scene: "社交 / companion、企业合规、医疗隐私",
        chat: [
          { n:"群", t:"项目统一用 Slack 沟通（共识）" },
          { n:"Alice", t:"（私下·不含 Carol）我更习惯飞书；在看新机会，别让 Carol 知道" },
        ],
        qa: [ { q:"项目用什么工具？", a:"Slack（群规范）" }, { q:"Carol 问 Alice 近况？", a:"不泄漏跳槽" } ],
        difficulty: "群体级 ≠ 个体级，易混；且回答要看「谁在问」。现有系统既会把群规范当个人偏好，也会无差别泄漏隐私。",
        solution: "group_insight（群规范）与 per_speaker_core（个体）分层 + audience_set 访问控制 + R_leak 泄漏惩罚。",
        domains: ["社交 / companion","企业合规(GDPR)","医疗隐私","多租户助手"],
      },
    ];

    const spkPalette = [C.cyan, C.amber, C.violet, C.green, C.cyanDk, C.navy];
    EXAMPLES.forEach((cfg, i) => {
      const s = pres.addSlide();
      s.background = { color: C.white };
      header(s, `核心能力示例 ${i+1} / 6 · ${cfg.type}`, cfg.title, cfg.accent);
      s.addText([{ text:"场景：", options:{ bold:true, color:C.muted } }, { text:cfg.scene, options:{ color:C.muted } }], { x:M, y:1.44, w:5.4, h:0.24, fontSize:9, fontFace:F.body, margin:0, valign:"middle" });

      // chat bubbles
      const cmap = {}; let ci = 0;
      const top = 1.82, bottom = 3.74, n = cfg.chat.length, slot = (bottom - top) / n;
      cfg.chat.forEach((b, k) => {
        if (cmap[b.n] === undefined) { cmap[b.n] = spkPalette[ci % spkPalette.length]; ci++; }
        const col = cmap[b.n];
        const bh = Math.min(slot - 0.08, 0.58);
        const y = top + k*slot + (slot - bh)/2;
        s.addShape(OVAL, { x:M, y:y, w:0.36, h:0.36, fill:{color:col}, line:{type:"none"} });
        s.addText(b.n.slice(0,1), { x:M, y:y, w:0.36, h:0.36, fontSize:11, bold:true, color:C.white, align:"center", valign:"middle", fontFace:F.head, margin:0 });
        s.addShape(ROUND, { x:M+0.46, y:y-0.03, w:4.85, h:bh+0.06, fill:{color:C.panel2}, line:{color:C.line, width:0.5}, rectRadius:0.06 });
        s.addText([{ text:b.n+"：", options:{ bold:true, color:col } }, { text:b.t, options:{ color:C.ink2 } }], { x:M+0.6, y:y-0.03, w:4.6, h:bh+0.06, fontSize:8.6, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
      });

      // Q/A strip
      card(s, M, 3.88, 5.31, 0.54, { fill:C.dark, shadow:true, lineCol:null });
      const qaRuns = [];
      cfg.qa.forEach((p, k) => {
        qaRuns.push({ text:"Q ", options:{ bold:true, color:cfg.accent } });
        qaRuns.push({ text:p.q+"  →  ", options:{ color:"DDE6F5" } });
        qaRuns.push({ text:p.a, options:{ bold:true, color:C.cyan, breakLine: k < cfg.qa.length-1 } });
      });
      s.addText(qaRuns, { x:M+0.2, y:3.88, w:5.31-0.36, h:0.54, fontSize:8.6, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.12 });

      // right: difficulty
      const rx = 6.05, rw = W-M-rx;
      card(s, rx, 1.55, rw, 1.42, { accent:C.red, fill:C.redBg, lineCol:null });
      s.addText("难点 · 现有系统为何失败", { x:rx+0.2, y:1.64, w:rw-0.36, h:0.28, fontSize:11, bold:true, color:C.red, fontFace:F.head, margin:0 });
      s.addText(cfg.difficulty, { x:rx+0.2, y:1.95, w:rw-0.38, h:0.98, fontSize:8.4, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.1 });

      // right: solution
      card(s, rx, 3.06, rw, 1.36, { accent:C.cyan, fill:C.cyanBg, lineCol:null });
      s.addText("SpeakerMem-R1 怎么解", { x:rx+0.2, y:3.15, w:rw-0.36, h:0.28, fontSize:11, bold:true, color:C.cyanDk, fontFace:F.head, margin:0 });
      s.addText(cfg.solution, { x:rx+0.2, y:3.46, w:rw-0.38, h:0.92, fontSize:8.4, color:C.ink2, fontFace:F.body, margin:0, valign:"top", lineSpacingMultiple:1.1 });

      // bottom: domains
      card(s, M, 4.5, W-2*M, 0.42, { fill:C.panel, accent:cfg.accent, lineCol:null });
      s.addText([{ text:"适用领域： ", options:{ bold:true, color:C.ink } }, { text:cfg.domains.join("　·　"), options:{ color:C.ink2 } }], { x:M+0.18, y:4.5, w:W-2*M-0.34, h:0.42, fontSize:9, fontFace:F.body, margin:0, valign:"middle" });
      footer(s);
    });
  }

  // =================================================================
  // SLIDE 12 — Method: three contributions
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法 SpeakerMem-R1 · 核心创新", "三大技术贡献：奖励 · 信用分配 · 记忆结构", C.cyan);

    const cons = [
      ["scale", C.cyan, C.cyanBg, "BCE3EC", "①", "SpeakerLevenshtein 奖励", "per-speaker 分桶的稠密奖励，区分「归因错误」与「事实错误」，并设 worst-speaker bonus 防止忽略最难说话人。", "DeltaMem 的 flat Levenshtein"],
      ["diagram", C.violet, C.violetBg, "CFC8F1", "②", "Speaker-Conditioned LoGo-GRPO", "local rerollout 按 active speaker set 分层，保证组内比较「相同说话人分布」，奖励才可比。", "Memory-R2 的 LoGo"],
      ["layers", C.amber, C.amberBg, "E9C99A", "③", "5 层 Speaker-Indexed Memory", "per-speaker（core / episodic / profile）+ group（interaction / insight），直接对应 5 类失败模式。", "平铺 fact store → 层次化"],
    ];
    const cw = (W-2*M-2*0.3)/3;
    cons.forEach((c, i) => {
      const x = M + i*(cw+0.3), y=1.55, h=3.32;
      card(s, x, y, cw, h, { shadow:true });
      s.addShape(RECT, { x, y, w:cw, h:0.12, fill:{color:c[1]} });
      iconChip(s, x+0.24, y+0.34, 0.74, IC[c[0]][c[1]], { bg:c[2], pad:0.19 });
      s.addText(c[4], { x:x+cw-0.86, y:y+0.3, w:0.64, h:0.6, fontSize:30, bold:true, color:c[3], align:"right", fontFace:F.num, margin:0 });
      s.addText(c[5], { x:x+0.24, y:y+1.22, w:cw-0.46, h:0.62, fontSize:13, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"top", lineSpacingMultiple:1.0 });
      s.addText(c[6], { x:x+0.24, y:y+1.92, w:cw-0.46, h:0.92, fontSize:9.8, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.06 });
      s.addShape(LINE, { x:x+0.24, y:y+2.88, w:cw-0.48, h:0, line:{color:C.line, width:1} });
      s.addImage({ data: IC.arrow[c[1]], x:x+0.24, y:y+3.0, w:0.2, h:0.18 });
      s.addText([{ text:"扩展自 ", options:{ color:C.muted } }, { text:c[7], options:{ bold:true, color:c[1] } }], { x:x+0.5, y:y+2.92, w:cw-0.7, h:0.34, fontSize:9, fontFace:F.body, margin:0, valign:"middle" });
    });
    footer(s, 7);
  }

  // =================================================================
  // SLIDE 11 — Method expand 1: SpeakerLevenshtein
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 ① · 奖励", "SpeakerLevenshtein：按说话人分桶的稠密奖励", C.cyan);

    const lx=M, lw=4.95, ly=1.55;
    card(s, lx, ly, lw, 3.36, { shadow:true });
    s.addText("总状态奖励  R_state", { x:lx+0.22, y:ly+0.16, w:lw-0.44, h:0.3, fontSize:12, bold:true, color:C.ink, fontFace:F.head, margin:0 });
    card(s, lx+0.22, ly+0.54, lw-0.44, 0.5, { fill:C.panel, shadow:false, lineCol:null });
    s.addText("R_state = avg_s(LevF1_s) + μ·min_s(LevF1_s) + R_leak", { x:lx+0.34, y:ly+0.54, w:lw-0.68, h:0.5, fontSize:9.6, bold:true, color:C.cyanDk, fontFace:"Consolas", margin:0, valign:"middle" });
    const terms = [
      [C.cyan, "avg_s(LevF1_s)", "按说话人均值：每个说话人单独算 Levenshtein F1"],
      [C.amber, "μ·min_s(LevF1_s)", "worst-speaker bonus：防止在最难说话人上「摆烂」"],
      [C.red, "R_leak", "跨说话人泄漏惩罚：Alice 的事进 Bob 桶则扣分"],
    ];
    terms.forEach((t, i) => {
      const y = ly+1.24 + i*0.6;
      s.addShape(RECT, { x:lx+0.22, y:y, w:0.06, h:0.48, fill:{color:t[0]} });
      s.addText(t[1], { x:lx+0.4, y:y-0.02, w:lw-0.6, h:0.26, fontSize:10, bold:true, color:t[0], fontFace:"Consolas", margin:0 });
      s.addText(t[2], { x:lx+0.4, y:y+0.22, w:lw-0.62, h:0.26, fontSize:8.5, color:C.ink2, fontFace:F.body, margin:0 });
    });
    s.addText("LevF1_s：在嵌入余弦相似度上做 optimal transport（Hungarian）匹配 + 阈值 τ + 词面保真度（沿用 DeltaMem）。", { x:lx+0.22, y:ly+3.0, w:lw-0.44, h:0.32, fontSize:7.8, italic:true, color:C.muted, fontFace:F.body, margin:0, lineSpacingMultiple:1.0 });

    const rx=lx+lw+0.3, rw=W-M-rx, ry=1.55;
    s.addText("为什么 per-speaker 不是 trivial（朴素拼接会失败）", { x:rx, y:ry, w:rw, h:0.28, fontSize:10.5, bold:true, color:C.muted, fontFace:F.body, margin:0 });
    const why = [
      ["归属-内容混淆", "全局 Levenshtein 对「事实错」（Alice→Google 而非 ByteDance）与「归属错」（Alice 的事进 Bob 桶）施加相同惩罚 —— agent 学不会该先修哪个。"],
      ["说话人不均衡", "跨说话人平均 → 在 K−1 个简单说话人成功、却忽略最难的那个。worst-speaker bonus 显式纠正这一退化。"],
    ];
    why.forEach((w, i) => {
      const y = ry+0.34 + i*1.02, h=0.92;
      card(s, rx, y, rw, h, { accent:C.amber, fill:C.amberBg, lineCol:null });
      s.addText(String(i+1), { x:rx+0.18, y:y+0.16, w:0.4, h:0.4, fontSize:20, bold:true, color:C.amber, fontFace:F.num, margin:0 });
      s.addText(w[0], { x:rx+0.62, y:y+0.12, w:rw-0.8, h:0.28, fontSize:11, bold:true, color:C.amberDk, fontFace:F.head, margin:0 });
      s.addText(w[1], { x:rx+0.62, y:y+0.38, w:rw-0.82, h:0.5, fontSize:8.5, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.04 });
    });
    card(s, rx, ry+2.54, rw, 0.82, { fill:C.dark, shadow:false, lineCol:null });
    s.addText([
      { text:"数据支撑：", options:{ bold:true, color:C.cyan } },
      { text:"GroupMemBench 上归属错误是主要失败模式 —— 知识更新类 27.1%、术语歧义类 37.7%。", options:{ color:"D7DEEF" } },
    ], { x:rx+0.2, y:ry+2.54, w:rw-0.38, h:0.82, fontSize:9.2, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.06 });
    footer(s);
  }

  // =================================================================
  // SLIDE 12 — Method expand 2: Speaker-Conditioned LoGo-GRPO
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 ② · 信用分配", "SC-LoGo-GRPO：公平比较是逻辑必然，非便利", C.cyan);

    card(s, M, 1.5, W-2*M, 1.0, { fill:C.dark, shadow:true, lineCol:null });
    s.addImage({ data: IC.bulb[C.amber], x:M+0.24, y:1.68, w:0.4, h:0.4 });
    s.addText([
      { text:"为什么说话人条件化是逻辑必然：", options:{ bold:true, color:C.amber } },
      { text:"Memory-R2 的 LoGo 只保证「相同起始记忆状态」；多方还要求「相同 active speaker set」—— 因为「只有 Alice 发言的一轮」与「Alice、Bob 互相谈论的一轮」记忆操作策略本质不同。没有它，组内比较与全局比较一样不公平。", options:{ color:"DDE6F5" } },
    ], { x:M+0.8, y:1.5, w:W-2*M-1.0, h:1.0, fontSize:10.3, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.1 });

    const cw=(W-2*M-0.3)/2, y=2.72, h=1.36;
    card(s, M, y, cw, h, { accent:C.violet });
    s.addText("① 说话人条件化 local rerollout", { x:M+0.2, y:y+0.16, w:cw-0.4, h:0.3, fontSize:11.5, bold:true, color:C.violet, fontFace:F.head, margin:0 });
    s.addText("G 个 local rollout 共享同一中间记忆状态 M_m，并且共享同一 active speaker set —— 保证相同语境内的公平比较。", { x:M+0.2, y:y+0.5, w:cw-0.4, h:0.5, fontSize:9.2, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.06 });
    card(s, M+0.2, y+1.02, cw-0.4, 0.28, { fill:C.violetBg, shadow:false, lineCol:null });
    s.addText("T_local = {r_1,…,r_G}  from  (M_m, 后续轮次, speakers)", { x:M+0.3, y:y+1.02, w:cw-0.6, h:0.28, fontSize:8.2, color:C.violet, fontFace:"Consolas", margin:0, valign:"middle" });

    const x2=M+cw+0.3;
    card(s, x2, y, cw, h, { accent:C.cyan });
    s.addText("② 按说话人自适应信用（借 CoMAM）", { x:x2+0.2, y:y+0.16, w:cw-0.4, h:0.3, fontSize:11.5, bold:true, color:C.cyanDk, fontFace:F.head, margin:0 });
    s.addText("用「每个说话人 local reward 与 global reward 的对齐度」算信用权重：贡献越大的说话人，获得越多梯度信号。", { x:x2+0.2, y:y+0.5, w:cw-0.4, h:0.5, fontSize:9.2, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.06 });
    card(s, x2+0.2, y+1.02, cw-0.4, 0.28, { fill:C.cyanBg, shadow:false, lineCol:null });
    s.addText("α_s = normalize( Spearman( R_local_s , R_global ) )", { x:x2+0.3, y:y+1.02, w:cw-0.6, h:0.28, fontSize:8.2, color:C.cyanDk, fontFace:"Consolas", margin:0, valign:"middle" });

    card(s, M, 4.5, W-2*M, 0.42, { fill:C.panel, accent:C.navy, lineCol:null });
    s.addText([
      { text:"联合目标   ", options:{ bold:true, color:C.ink } },
      { text:"L_total = L_global + λ·L_local + β·L_KL", options:{ color:C.navy, bold:true, fontFace:"Consolas" } },
      { text:"    （KL 正则项防止 Echo Trap）", options:{ color:C.muted } },
    ], { x:M+0.2, y:4.5, w:W-2*M-0.4, h:0.42, fontSize:10, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDE 13 — Method expand 3: 5-layer memory + complete reward
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 ③ · 记忆结构 & 总奖励", "5 层记忆精准对应 5 类失败模式 + 完整奖励", C.cyan);

    const lx=M, lw=5.55, ly=1.55;
    const Hd=(t)=>({ text:t, options:{ fill:{color:C.dark}, color:C.white, bold:true, fontSize:9, align:"left", valign:"middle", fontFace:F.head } });
    const cl=(t,o={})=>({ text:t, options:{ fontSize:8.6, color:o.color||C.ink2, align:"left", valign:"middle", fontFace:o.mono?"Consolas":F.body, bold:o.bold||false, fill:{color:o.fill||C.white} } });
    const rows = [
      [Hd("记忆层"), Hd("作用域 · 内容"), Hd("对应失败模式")],
      [cl("M_core^s",{bold:true,color:C.cyanDk,mono:true}), cl("单说话人 · 持久事实"), cl("单流混淆",{color:C.red,bold:true})],
      [cl("M_episodic^s",{bold:true,color:C.cyanDk,mono:true,fill:C.panel2}), cl("单说话人 · 时间情节",{fill:C.panel2}), cl("时序状态覆盖",{color:C.red,bold:true,fill:C.panel2})],
      [cl("M_profile^s",{bold:true,color:C.cyanDk,mono:true}), cl("单说话人 · 风格偏好"), cl("实体合并（唯一 owner）",{color:C.red,bold:true})],
      [cl("M_interact",{bold:true,color:C.violet,mono:true,fill:C.panel2}), cl("群组 · 跨说话人关系",{fill:C.panel2}), cl("跨人格知识鸿沟",{color:C.red,bold:true,fill:C.panel2})],
      [cl("M_insight",{bold:true,color:C.violet,mono:true}), cl("群组 · 高层元知识"), cl("规范-个体混淆",{color:C.red,bold:true})],
    ];
    s.addTable(rows, { x:lx, y:ly, w:lw, colW:[1.55, 2.15, 1.85], rowH:[0.3,0.45,0.45,0.45,0.45,0.45], border:{type:"solid", color:C.line, pt:0.5}, valign:"middle", margin:[2,4,2,4], autoPage:false });
    s.addText("每条目 =（s_owner, content, 受众集合 A_e, 层 l_e, 轮次 t_e），受众集合即显式访问控制。", { x:lx, y:ly+2.62, w:lw, h:0.28, fontSize:7.9, italic:true, color:C.muted, fontFace:F.body, margin:0 });

    const rx=lx+lw+0.3, rw=W-M-rx, ry=1.55;
    card(s, rx, ry, rw, 3.35, { fill:C.dark, shadow:true, lineCol:null });
    s.addText("完整奖励函数", { x:rx+0.22, y:ry+0.18, w:rw-0.4, h:0.3, fontSize:12, bold:true, color:C.white, fontFace:F.head, margin:0 });
    const rterms = [
      ["0.5 · R_task", "outcome：答案 token-level F1", "AEB8D4"],
      ["0.8 · R_state", "稠密过程（主导）：SpeakerLevenshtein", C.cyan],
      ["0.3 · R_attr", "说话人归属准确率", C.amber],
      ["0.2 · R_aud", "受众适配得分", C.amber],
      ["0.1·R_compr + 0.1·R_RIF", "结构：压缩率 + 遗忘恰当性", "AEB8D4"],
    ];
    rterms.forEach((t, i) => {
      const y = ry+0.6 + i*0.46;
      s.addText(t[0], { x:rx+0.22, y:y, w:rw-0.44, h:0.22, fontSize:9.3, bold:true, color:t[2], fontFace:"Consolas", margin:0 });
      s.addText(t[1], { x:rx+0.22, y:y+0.19, w:rw-0.44, h:0.22, fontSize:8, color:"AEB8D4", fontFace:F.body, margin:0 });
    });
    s.addText([
      { text:"R_state 权重 0.8 主导：", options:{ bold:true, color:C.cyan } },
      { text:"DeltaMem 实证 —— 稠密过程奖励比 outcome 更快收敛。", options:{ color:"C7D0E8" } },
    ], { x:rx+0.22, y:ry+2.98, w:rw-0.42, h:0.3, fontSize:8, fontFace:F.body, margin:0, valign:"middle" });
    footer(s);
  }

  // =================================================================
  // SLIDE 14 — Method: 3-stage training
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法 SpeakerMem-R1 · 训练流程", "三阶段：SFT 热启动 → Joint RL → 端到端", C.cyan);

    const stages = [
      ["Stage 1", "SFT 热启动", C.cyan, C.cyanBg, "role-masked SFT（借用 MuPaS），用合成数据热启动。", "通过标准：speaker attribution F1 > 50%"],
      ["Stage 2", "Joint RL", C.violet, C.violetBg, "SpeakerMem-GRPO，二维课程逐步加难。", "课程：说话人 K=3→5→8 × session 8→16→32"],
      ["Stage 3", "端到端联合", C.amber, C.amberBg, "Construction + Retrieval + Answer 联合优化。", "三个子模块端到端协同，回填全部指标"],
    ];
    const cw = 2.86, gapx=(W-2*M-3*cw)/2, y=1.6, h=2.6;
    stages.forEach((st, i) => {
      const x = M + i*(cw+gapx);
      card(s, x, y, cw, h, { shadow:true });
      s.addShape(RECT, { x, y, w:cw, h:0.52, fill:{color:st[2]} });
      s.addText(st[0], { x:x+0.2, y:y, w:cw-0.4, h:0.52, fontSize:13, bold:true, color:C.white, valign:"middle", fontFace:F.num, margin:0 });
      s.addText(st[1], { x:x+0.2, y:y+0.64, w:cw-0.4, h:0.34, fontSize:14.5, bold:true, color:C.ink, fontFace:F.head, margin:0 });
      s.addText(st[4], { x:x+0.2, y:y+1.02, w:cw-0.4, h:0.66, fontSize:10, color:C.ink2, fontFace:F.body, margin:0, lineSpacingMultiple:1.06 });
      card(s, x+0.2, y+1.74, cw-0.4, 0.66, { fill:st[3], shadow:false, lineCol:null });
      s.addText(st[5], { x:x+0.32, y:y+1.74, w:cw-0.64, h:0.66, fontSize:9, bold:true, color:C.ink2, valign:"middle", fontFace:F.body, margin:0, lineSpacingMultiple:1.02 });
      if (i < 2) s.addImage({ data: IC.arrow[C.faint], x:x+cw+gapx/2-0.16, y:y+1.0, w:0.32, h:0.3 });
    });

    card(s, M, 4.42, W-2*M, 0.5, { fill:C.cyanBg, accent:C.cyan, lineCol:null });
    s.addImage({ data: IC.bulb[C.cyanDk], x:M+0.2, y:4.5, w:0.34, h:0.34 });
    s.addText([
      { text:"写作优势：", options:{ bold:true, color:C.cyanDk } },
      { text:"每个贡献都有对应的 dyadic 前置工作可对比，差异清晰 —— 利于回应「这不就是加个 speaker_id 吗」的质疑。", options:{ color:C.ink2 } },
    ], { x:M+0.66, y:4.42, w:W-2*M-0.85, h:0.5, fontSize:10, fontFace:F.body, margin:0, valign:"middle" });
    footer(s, 8);
  }

  // =================================================================
  // SLIDE 17 — Method: RL training loop walkthrough
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "方法展开 · 训练循环", "一条数据在 RL 里怎么走一遍（Stage 2）", C.cyan);

    const lx=M, lw=5.95, ly=1.6;
    const steps = [
      ["一条对话 → policy 逐轮处理 = 一条完整轨迹；采样 G=4 条", C.cyan],
      ["每条轨迹用完整奖励 R 打分 → 4 个分数", C.cyan],
      ["group-relative：高于这组均值 → 正 advantage，低于 → 负", C.cyan],
      ["GRPO：抬高高分轨迹里的记忆动作概率，压低低分的", C.cyan],
      ["SC-LoGo 局部分支：中段固定「相同记忆 + 相同在场说话人」再分叉比较", C.violet],
      ["L_total = L_global + λ·L_local + β·KL → 更新这一个模型", C.amber],
    ];
    steps.forEach((st, i) => {
      const y = ly + i*0.565;
      s.addShape(OVAL, { x:lx, y:y, w:0.4, h:0.4, fill:{color:st[1]}, line:{type:"none"} });
      s.addText(String(i+1), { x:lx, y:y, w:0.4, h:0.4, fontSize:15, bold:true, color:C.white, align:"center", valign:"middle", fontFace:F.num, margin:0 });
      if (i < 5) s.addShape(LINE, { x:lx+0.2, y:y+0.4, w:0, h:0.165, line:{color:C.line, width:1.5} });
      s.addText(st[0], { x:lx+0.56, y:y, w:lw-0.56, h:0.4, fontSize:9.7, color:C.ink2, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
    });

    const rx=lx+lw+0.3, rw=W-M-rx, ry=1.6;
    card(s, rx, ry, rw, 3.3, { fill:C.dark, shadow:true, lineCol:null });
    s.addText("奖励 = 打分老师", { x:rx+0.22, y:ry+0.2, w:rw-0.4, h:0.3, fontSize:12, bold:true, color:C.white, fontFace:F.head, margin:0 });
    card(s, rx+0.22, ry+0.58, rw-0.44, 0.66, { fill:C.dark2, shadow:false, lineCol:null });
    s.addText([
      { text:"R = 0.5·R_task + 0.8·R_state", options:{ breakLine:true } },
      { text:"      + 0.3·R_attr + 0.2·R_aud …", options:{} },
    ], { x:rx+0.34, y:ry+0.58, w:rw-0.66, h:0.66, fontSize:8.5, bold:true, color:C.cyan, fontFace:"Consolas", margin:0, valign:"middle", lineSpacingMultiple:1.15 });
    const notes = [
      [C.cyan, "R_state（主导）", "逐轮、按说话人分桶的稠密反馈"],
      [C.amber, "R_task", "episode 末的结果反馈"],
      [C.green, "标准答案", "全部来自合成数据的标注"],
    ];
    notes.forEach((n, i) => {
      const y = ry+1.5 + i*0.58;
      s.addShape(OVAL, { x:rx+0.24, y:y+0.03, w:0.13, h:0.13, fill:{color:n[0]}, line:{type:"none"} });
      s.addText(n[1], { x:rx+0.46, y:y-0.05, w:rw-0.66, h:0.24, fontSize:10, bold:true, color:n[0], fontFace:F.head, margin:0 });
      s.addText(n[2], { x:rx+0.46, y:y+0.19, w:rw-0.66, h:0.26, fontSize:8.3, color:"C7D0E8", fontFace:F.body, margin:0 });
    });
    footer(s);
  }

  // =================================================================
  // SLIDE 18 — Deliverables
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "已完成产出清单 · Deliverables", "代码 6 模块 + 论文 7 章（实验数字待填）", C.cyan);

    // left: code
    const lx=M, lw=4.5, ly=1.55;
    card(s, lx, ly, lw, 2.55, { shadow:true });
    iconChip(s, lx+0.2, ly+0.2, 0.56, IC.code[C.cyanDk], { bg:C.cyanBg, pad:0.14 });
    s.addText("代码框架 · 6 模块", { x:lx+0.88, y:ly+0.2, w:lw-1.6, h:0.3, fontSize:13.5, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
    pill(s, lx+lw-1.5, ly+0.24, 1.32, 0.3, "dry-run / mock 通过", { bg:C.greenBg, fg:C.green, fs:8.5 });
    const mods = [
      ["speaker_levenshtein.py", "SpeakerLevenshtein 奖励函数"],
      ["speaker_aware_memory.py", "5 层记忆数据结构"],
      ["synthetic_data_pipeline.py", "合成数据 pipeline（接 GPT-4）"],
      ["memory_agent.py", "3 阶段 Agent"],
      ["grpo_trainer.py", "SC-LoGo-GRPO 训练循环"],
      ["evaluation.py", "三个多方 benchmark 评测接口"],
    ];
    mods.forEach((m, i) => {
      const y = ly+0.72 + i*0.3;
      s.addImage({ data: IC.check[C.green], x:lx+0.24, y:y+0.03, w:0.18, h:0.18 });
      s.addText(m[0], { x:lx+0.5, y:y, w:2.45, h:0.26, fontSize:9.5, bold:true, color:C.ink, fontFace:"Consolas", margin:0, valign:"middle" });
      s.addText(m[1], { x:lx+2.55, y:y, w:lw-2.7, h:0.26, fontSize:8.5, color:C.muted, fontFace:F.body, margin:0, valign:"middle" });
    });

    // right: paper
    const rx=lx+lw+0.3, rw=W-M-rx;
    card(s, rx, ly, rw, 2.55, { shadow:true });
    iconChip(s, rx+0.2, ly+0.2, 0.56, IC.file[C.violet], { bg:C.violetBg, pad:0.14 });
    s.addText("论文草稿 · 7 章成稿", { x:rx+0.88, y:ly+0.2, w:rw-1.6, h:0.3, fontSize:13.5, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
    const chs = [
      "Abstract + Introduction",
      "Related Work（含 R²-Mem 更新）",
      "Method（§3.1–3.8，含完整公式）",
      "Experiments（9 baseline · 7 消融 · 3 case 框架）",
      "Conclusion ＋ Appendix（§A–E）",
      "AAAI 写作指南 ＋ 31 条 BibTeX",
    ];
    chs.forEach((c, i) => {
      const y = ly+0.72 + i*0.3;
      s.addImage({ data: IC.check[C.violet], x:rx+0.24, y:y+0.03, w:0.18, h:0.18 });
      s.addText(c, { x:rx+0.5, y:y, w:rw-0.7, h:0.26, fontSize:9.5, color:C.ink2, fontFace:F.body, margin:0, valign:"middle" });
    });

    // bottom strip: gap
    card(s, M, 4.34, W-2*M, 0.56, { fill:C.redBg, accent:C.red, lineCol:null });
    s.addImage({ data: IC.times[C.red], x:M+0.22, y:4.46, w:0.32, h:0.32 });
    s.addText([
      { text:"尚缺：", options:{ bold:true, color:C.red } },
      { text:"所有模块均未真实训练，所有实验数字为占位符 —— 这是距「Highlight」的唯一差距。", options:{ color:C.ink2 } },
    ], { x:M+0.66, y:4.34, w:W-2*M-0.85, h:0.56, fontSize:10.5, bold:true, fontFace:F.body, margin:0, valign:"middle" });
    footer(s, 9);
  }

  // =================================================================
  // SLIDE 10 — Self assessment (manual bar chart)
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "当前自评 · 距 Highlight 的差距全在实验", "Soundness 是唯一硬伤，差实验数字", C.amber);

    // manual horizontal bars
    const bx=M+0.05, by=1.75, labelW=1.5, barX=bx+labelW, barMax=3.0, rowH=0.7;
    const dims = [
      ["Novelty", 9, C.cyan, "零篇先行者"],
      ["Significance", 8.5, C.cyan, "三 benchmark 证明系统性失败"],
      ["Soundness", 6.5, C.red, "实验全未做 — 唯一硬伤"],
      ["Clarity", 8.5, C.cyan, "概念统一 speaker-grounded"],
    ];
    // scale guide line at 8 (highlight threshold)
    const gx = barX + (8/10)*barMax;
    s.addShape(LINE, { x:gx, y:by-0.12, w:0, h:rowH*4-0.05, line:{color:C.amber, width:1, dashType:"dash"} });
    s.addText("Highlight 线 ≈ 8", { x:gx-0.7, y:by-0.42, w:1.6, h:0.24, fontSize:8, bold:true, color:C.amberDk, align:"center", fontFace:F.body, margin:0 });
    dims.forEach((d, i) => {
      const y = by + i*rowH;
      s.addText(d[0], { x:bx-0.05, y:y, w:labelW, h:0.5, fontSize:11, bold:true, color:C.ink, valign:"middle", fontFace:F.head, margin:0 });
      s.addShape(RECT, { x:barX, y:y+0.08, w:barMax, h:0.34, fill:{color:C.panel}, line:{type:"none"} });
      const bw = (d[1]/10)*barMax;
      s.addShape(RECT, { x:barX, y:y+0.08, w:bw, h:0.34, fill:{color:d[2]} });
      s.addText(d[1].toFixed(1).replace(/\.0$/,"")+" / 10", { x:barX+bw+0.08, y:y+0.05, w:1.0, h:0.4, fontSize:10.5, bold:true, color:d[2], valign:"middle", fontFace:F.num, margin:0 });
      s.addText(d[3], { x:barX, y:y+0.42, w:barMax+0.9, h:0.24, fontSize:8, color:C.muted, fontFace:F.body, margin:0 });
    });

    // right callout
    const rx=6.55, rw=W-M-rx, ry=1.62;
    card(s, rx, ry, rw, 3.28, { fill:C.dark, shadow:true, lineCol:null });
    s.addText("综合评估 · V9", { x:rx+0.28, y:ry+0.24, w:rw-0.5, h:0.3, fontSize:12, bold:true, color:C.faint, fontFace:F.body, margin:0 });
    s.addText("7.75", { x:rx+0.24, y:ry+0.52, w:rw-0.48, h:0.72, fontSize:42, bold:true, color:C.cyan, fontFace:F.num, margin:0, valign:"middle" });
    s.addText("区间 7.4–7.75 ·「强提交」级", { x:rx+0.28, y:ry+1.32, w:rw-0.52, h:0.42, fontSize:10.5, bold:true, color:C.white, fontFace:F.head, margin:0, lineSpacingMultiple:1.0 });
    s.addShape(LINE, { x:rx+0.28, y:ry+1.82, w:rw-0.56, h:0, line:{color:"33407A", width:1} });
    const notes = [
      [C.green, "Novelty / Significance / Clarity 三项已达标"],
      [C.red, "Soundness 6–7：实验全未做"],
      [C.amber, "补上实验即可整体迈过 Highlight 线"],
    ];
    notes.forEach((n, i) => {
      const y = ry+1.94 + i*0.44;
      s.addShape(OVAL, { x:rx+0.28, y:y+0.05, w:0.13, h:0.13, fill:{color:n[0]}, line:{type:"none"} });
      s.addText(n[1], { x:rx+0.52, y:y-0.04, w:rw-0.78, h:0.46, fontSize:9.8, color:"D7DEEF", fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
    });
    footer(s, 10);
  }

  // =================================================================
  // SLIDE 11 — Risks
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "关键风险与应对 · Risks", "已为每个风险准备退路", C.amber);

    const risks = [
      ["shield", "RL 训练不收敛", "中", C.amber, "退路：只做 SFT + 轻量 RL，或转「benchmark 分析型」论文（仍可发 AAAI）。"],
      ["db", "合成训练数据质量不足", "中", C.amber, "多源校验 + 人工抽检；必要时人工标注一小批种子数据兜底。"],
      ["bolt", "竞争者 7 月前抢发", "低 ~10%", C.green, "一旦有初步结果立即 arXiv preprint 占坑。"],
      ["clock", "时间窗口紧（约 7 周）", "高", C.red, "取决于时间线决策（见下一页路线图与待定问题）。"],
      ["flask", "算力 / 经费不到位", "待定", C.muted, "取决于实验室资源，待导师确认（约 4×A100 / ~$1,100）。"],
    ];
    const cw = (W-2*M-0.3)/2;
    risks.forEach((r, i) => {
      const col = i % 2, row = Math.floor(i/2);
      const x = M + col*(cw+0.3), y = 1.58 + row*0.84, h=0.72;
      card(s, x, y, cw, h, { accent:r[3] });
      iconChip(s, x+0.16, y+0.16, 0.4, IC[r[0]][r[3]===C.muted?C.muted:r[3]], { bg:C.panel, pad:0.1 });
      s.addText(r[1], { x:x+0.66, y:y+0.1, w:cw-2.0, h:0.3, fontSize:11.5, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
      pill(s, x+cw-1.28, y+0.13, 1.12, 0.26, "概率 "+r[2], { bg: r[3]===C.muted?C.panel:(r[3]===C.red?C.redBg:(r[3]===C.green?C.greenBg:C.amberBg)), fg: r[3]===C.muted?C.muted:r[3], fs:8.5 });
      s.addText(r[4], { x:x+0.66, y:y+0.38, w:cw-0.82, h:0.32, fontSize:8.8, color:C.ink2, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
    });

    // emphasis box (5th risk spans nicely; add a summary callout in last cell area)
    const x = M + 1*(cw+0.3), y = 1.58 + 2*0.84;
    card(s, x, y, cw, 0.72, { fill:C.cyanBg, accent:C.cyan, lineCol:null });
    s.addImage({ data: IC.check[C.cyanDk], x:x+0.18, y:y+0.2, w:0.32, h:0.32 });
    s.addText([
      { text:"整体姿态：", options:{ bold:true, color:C.cyanDk } },
      { text:"每条风险都有可执行退路，最大不确定性集中在「时间线 + 算力」两项 —— 正是需导师拍板处。", options:{ color:C.ink2 } },
    ], { x:x+0.62, y:y, w:cw-0.78, h:0.72, fontSize:9.2, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.02 });
    footer(s, 11);
  }

  // =================================================================
  // SLIDE 12 — Roadmap / timeline
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.white };
    header(s, "下一步规划 · 三阶段路线图", "若冲刺 AAAI 2027：约 7 周窗口", C.cyan);

    const phases = [
      ["Phase 1", "即刻 – 7 月初", C.cyan, "实验准备", ["GPT-4 合成 200 条训练数据（~$50–100）", "下载 benchmark，跑通 BM25 / Mem0 baseline", "Qwen-7B/8B 完成 Stage 1 SFT"]],
      ["Phase 2", "7 – 9 月", C.violet, "核心实验（~4×A100 / ~$1,100）", ["Joint RL → 端到端训练", "三个多方 benchmark 主实验 + LoCoMo", "Top-3 必做消融"]],
      ["Phase 3", "9 – 11 月", C.amber, "写作投稿", ["回填全部实验数字", "arXiv preprint 占坑", "投稿 AAAI 2027"]],
    ];
    const cw = (W-2*M-2*0.3)/3;
    phases.forEach((p, i) => {
      const x = M + i*(cw+0.3), y=1.56, h=2.55;
      card(s, x, y, cw, h, { shadow:true });
      s.addShape(RECT, { x, y, w:cw, h:0.62, fill:{color:p[2]} });
      s.addText(p[0], { x:x+0.2, y:y+0.08, w:cw-0.4, h:0.3, fontSize:14, bold:true, color:C.white, fontFace:F.num, margin:0 });
      s.addText(p[1], { x:x+0.2, y:y+0.36, w:cw-0.4, h:0.24, fontSize:9.5, color:"F0F4FF", fontFace:F.body, margin:0 });
      s.addText(p[3], { x:x+0.2, y:y+0.72, w:cw-0.4, h:0.4, fontSize:10.5, bold:true, color:C.ink, fontFace:F.head, margin:0, valign:"middle" });
      p[4].forEach((t, j) => {
        const yy = y+1.18 + j*0.42;
        s.addShape(OVAL, { x:x+0.22, y:yy+0.04, w:0.1, h:0.1, fill:{color:p[2]}, line:{type:"none"} });
        s.addText(t, { x:x+0.4, y:yy-0.04, w:cw-0.58, h:0.42, fontSize:8.8, color:C.ink2, fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
      });
    });

    // deadline strip
    card(s, M, 4.36, W-2*M, 0.54, { fill:C.amberBg, accent:C.amber, lineCol:null });
    s.addImage({ data: IC.flag[C.amberDk], x:M+0.2, y:4.46, w:0.32, h:0.32 });
    s.addText([
      { text:"截止：", options:{ bold:true, color:C.amberDk } },
      { text:"Abstract 7/21 ｜ Full Paper 7/28 ｜ 代码附录 7/31（距今约 50 天）。 ", options:{ color:C.ink2 } },
      { text:"⚠ CFP 年份需官方核实 —— 直接决定是否冲刺。", options:{ bold:true, color:C.red } },
    ], { x:M+0.62, y:4.36, w:W-2*M-0.8, h:0.54, fontSize:9.8, fontFace:F.body, margin:0, valign:"middle" });
    footer(s, 12);
  }

  // =================================================================
  // SLIDE 13 — Questions for advisor (climax)
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.dark };
    s.addShape(RECT, { x:0, y:0, w:0.18, h:H, fill:{color:C.amber} });
    s.addShape(RECT, { x:M, y:0.44, w:0.15, h:0.15, fill:{color:C.amber} });
    s.addText("最需要导师拍板 · Decisions", { x:M+0.25, y:0.37, w:8, h:0.3, fontSize:11, color:C.amber, bold:true, charSpacing:1, fontFace:F.body, margin:0, valign:"middle" });
    s.addText("7 个核心问题，请导师定调", { x:M, y:0.74, w:W-2*M, h:0.56, fontSize:24, bold:true, color:C.white, fontFace:F.head, margin:0, valign:"middle" });

    const qs = [
      ["时间线取舍", "全力冲刺 AAAI 2027（风险高）vs 瞄准稍晚会议把实验做扎实？", true],
      ["算力与经费", "4×A100 + ~$1,100 训练 + ~$50–100 API，实验室可提供并排得上队？", true],
      ["训练数据策略", "纯合成能否支撑 RL 收敛？是否人工标注种子兜底？有无合作组真实数据？", true],
      ["基座模型", "Qwen2.5-7B-Instruct vs Qwen3-8B（对齐 DeltaMem 便于公平比较）？", false],
      ["备选 / 降级方案", "若 RL 不收敛：SFT-only + 轻量 RL，还是转「分析型」论文？", false],
      ["preprint 占坑", "是否同意一旦有初步结果即发 arXiv preprint？", false],
      ["是否拆第二篇", "SpeakerLevenshtein 独立成 short paper（EMNLP/ACL）并行推进？", false],
    ];
    const colW = (W-2*M-0.3)/2;
    qs.forEach((q, i) => {
      const col = i < 4 ? 0 : 1;
      const idx = col === 0 ? i : i-4;
      const x = M + col*(colW+0.3);
      const y = 1.46 + idx*0.84;
      const star = q[2];
      card(s, x, y, colW, 0.74, { fill: star?"23284F":C.dark2, shadow:false, lineCol: star?null:null, accent: star?C.amber:C.cyan });
      s.addShape(OVAL, { x:x+0.18, y:y+0.2, w:0.34, h:0.34, fill:{color: star?C.amber:C.cyan}, line:{type:"none"} });
      s.addText(String(i+1), { x:x+0.18, y:y+0.2, w:0.34, h:0.34, fontSize:13, bold:true, color:C.dark, align:"center", valign:"middle", fontFace:F.num, margin:0 });
      s.addText([
        { text: q[0] + (star?"  ★":""), options:{ bold:true, color: star?C.amber:C.cyan } },
      ], { x:x+0.64, y:y+0.08, w:colW-0.8, h:0.26, fontSize:11.5, fontFace:F.head, margin:0, valign:"middle" });
      s.addText(q[1], { x:x+0.64, y:y+0.34, w:colW-0.82, h:0.38, fontSize:8.8, color:"C7D0E8", fontFace:F.body, margin:0, valign:"middle", lineSpacingMultiple:1.0 });
    });
    s.addText("★ = 最高优先（直接决定项目能否冲刺）", { x:M, y:4.92, w:6, h:0.26, fontSize:9, italic:true, color:C.faint, fontFace:F.body, margin:0 });
    PG++;
    s.addText(`${PG} / ${TOTAL}`, { x:W-1.2, y:H-0.34, w:0.7, h:0.26, fontSize:8, color:C.faint, align:"right", fontFace:F.body, margin:0, valign:"middle" });
  }

  // =================================================================
  // SLIDE 14 — Closing
  // =================================================================
  {
    const s = pres.addSlide();
    s.background = { color: C.dark };
    s.addShape(OVAL, { x:-1.3, y:-1.3, w:3.4, h:3.4, fill:{color:C.navy, transparency:55}, line:{type:"none"} });
    s.addShape(OVAL, { x:8.4, y:3.6, w:3.0, h:3.0, fill:{color:C.cyanDk, transparency:62}, line:{type:"none"} });

    s.addText("一句话总结", { x:M+0.3, y:0.95, w:8, h:0.3, fontSize:12, bold:true, color:C.cyan, charSpacing:1, fontFace:F.body, margin:0 });
    s.addText("纸面准备已就位 —— novelty 零篇先行、7 章论文、6 模块代码；\n唯一缺口是实验。请导师就 时间线 / 算力 / 数据 三件事定调。", { x:M+0.3, y:1.35, w:8.7, h:1.1, fontSize:18, bold:true, color:C.white, fontFace:F.head, margin:0, lineSpacingMultiple:1.18 });

    // repo nav
    const navs = [
      ["file", "方法规格书", "SpeakerMem-R1-v2-方法spec.md"],
      ["book", "论文草稿 ×7", "论文草稿-*.md ＋ .bib"],
      ["search", "35 篇详解", "各论文 详解.md"],
      ["db", "数据 / 实验方案", "数据合成Pipeline · 50天冲刺指南"],
      ["code", "核心代码 ×6", "核心代码实现/"],
    ];
    const nw = (W-2*(M+0.3)-4*0.2)/5, ny=2.95, nh=1.18;
    navs.forEach((n, i) => {
      const x = M+0.3 + i*(nw+0.2);
      card(s, x, ny, nw, nh, { fill:C.dark2, shadow:false, lineCol:null });
      iconChip(s, x+(nw-0.5)/2, ny+0.16, 0.5, IC[n[0]][C.cyan], { bg:"23284F", pad:0.13 });
      s.addText(n[1], { x:x+0.05, y:ny+0.7, w:nw-0.1, h:0.24, fontSize:9.5, bold:true, color:C.white, align:"center", fontFace:F.head, margin:0 });
      s.addText(n[2], { x:x+0.05, y:ny+0.92, w:nw-0.1, h:0.24, fontSize:7, color:C.faint, align:"center", fontFace:F.body, margin:0 });
    });

    s.addShape(LINE, { x:M+0.3, y:4.55, w:W-2*M-0.6, h:0, line:{color:"31407A", width:1} });
    s.addText("感谢，期待您的指点", { x:M+0.3, y:4.7, w:6, h:0.4, fontSize:16, bold:true, color:C.white, fontFace:F.head, margin:0, valign:"middle" });
    s.addText("SpeakerMem-R1  ·  2026-06-02", { x:W-3.8, y:4.7, w:3.3, h:0.4, fontSize:10, color:C.faint, align:"right", valign:"middle", fontFace:F.body, margin:0 });
  }

  const out = process.argv[2] || "D:/ComputerScience/ZJUIDG/2026AAAI/SpeakerMem-R1-进度汇报-2026-06-02.pptx";
  await pres.writeFile({ fileName: out });
  console.log("WROTE:", out);
}

main().catch(e => { console.error(e); process.exit(1); });
