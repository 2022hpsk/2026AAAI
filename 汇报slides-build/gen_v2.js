/* SpeakerMem-R1 汇报 V2（问题导向 · 精简版）slides 生成器 */
const pptxgen = require("pptxgenjs");
const React = require("react");
const RDS = require("react-dom/server");
const sharp = require("sharp");
const FA = require("react-icons/fa");

const C = {
  dark:"12183A", dark2:"1C2550", navy:"27347A",
  ink:"1E293B", ink2:"334155", muted:"64748B", faint:"94A3B8",
  white:"FFFFFF", panel:"F1F5F9", panel2:"F8FAFC", line:"E2E8F0",
  cyan:"0EA5C4", cyanDk:"0E7490", cyanBg:"E0F4F9",
  amber:"E08A1E", amberDk:"B45309", amberBg:"FBEFD9",
  green:"0E9F6E", greenBg:"E1F5EC",
  red:"DC4A52", redBg:"FBE6E7",
  violet:"6D5BD0", violetBg:"ECE9FB",
};
const F = { head:"Microsoft YaHei", body:"Microsoft YaHei", num:"Arial Black" };
const W=10, H=5.625, M=0.5, TOTAL=13;
const RECT="rect", ROUND="roundRect", OVAL="ellipse", LINE="line";
const mkShadow = () => ({ type:"outer", color:"0F172A", blur:8, offset:3, angle:135, opacity:0.12 });

const iconCache={};
async function icon(Comp,hex){
  const key=(Comp.name||"x")+hex;
  if(iconCache[key]) return iconCache[key];
  const svg=RDS.renderToStaticMarkup(React.createElement(Comp,{color:"#"+hex,size:"256"}));
  const png=await sharp(Buffer.from(svg)).png().toBuffer();
  const d="image/png;base64,"+png.toString("base64"); iconCache[key]=d; return d;
}

async function main(){
  const pres=new pptxgen();
  pres.defineLayout({name:"W",width:W,height:H}); pres.layout="W";
  pres.author="SpeakerMem-R1"; pres.title="SpeakerMem-R1 汇报 V2";

  const IC={};
  const need=[["bulb",FA.FaLightbulb],["warn",FA.FaExclamationTriangle],["target",FA.FaBullseye],
    ["users",FA.FaUsers],["comments",FA.FaComments],["shield",FA.FaShieldAlt],["db",FA.FaDatabase],
    ["file",FA.FaFileAlt],["code",FA.FaCode],["layers",FA.FaLayerGroup],["scale",FA.FaBalanceScale],
    ["diagram",FA.FaProjectDiagram],["check",FA.FaCheckCircle],["arrow",FA.FaArrowRight],
    ["flask",FA.FaFlask],["chart",FA.FaChartBar],["flag",FA.FaFlagCheckered]];
  for(const [k,Comp] of need){ IC[k]={}; for(const col of [C.cyan,C.amber,C.green,C.red,C.violet,C.navy,C.white,C.muted,C.faint,C.cyanDk,C.amberDk]) IC[k][col]=await icon(Comp,col); }

  let PG=0;
  function footer(s,dark=false){
    PG++;
    const col=dark?C.faint:C.faint;
    s.addText("SpeakerMem-R1 · 问题导向汇报 V2 · 2026-06-03",{x:M,y:H-0.34,w:6,h:0.26,fontSize:8,color:col,fontFace:F.body,margin:0,valign:"middle"});
    s.addText(`${PG} / ${TOTAL}`,{x:W-1.2,y:H-0.34,w:0.7,h:0.26,fontSize:8,color:col,align:"right",fontFace:F.body,margin:0,valign:"middle"});
  }
  function header(s,kicker,title,accent=C.cyan){
    s.addShape(RECT,{x:M,y:0.44,w:0.15,h:0.15,fill:{color:accent}});
    s.addText(kicker,{x:M+0.25,y:0.37,w:W-2*M-0.25,h:0.3,fontSize:11,color:accent,bold:true,charSpacing:1,fontFace:F.body,margin:0,valign:"middle"});
    s.addText(title,{x:M,y:0.74,w:W-2*M,h:0.62,fontSize:23,bold:true,color:C.ink,fontFace:F.head,margin:0,valign:"middle"});
  }
  function card(s,x,y,w,h,opt={}){
    const {fill=C.white,accent=null,shadow=true,lineCol=C.line}=opt;
    s.addShape(RECT,{x,y,w,h,fill:{color:fill},line:lineCol?{color:lineCol,width:0.75}:{type:"none"},shadow:shadow?mkShadow():undefined});
    if(accent) s.addShape(RECT,{x,y,w:0.06,h,fill:{color:accent}});
  }
  function pill(s,x,y,w,h,text,opt={}){
    const {bg=C.cyanBg,fg=C.cyanDk,fs=9.5,bold=true}=opt;
    s.addShape(ROUND,{x,y,w,h,fill:{color:bg},line:{type:"none"},rectRadius:Math.min(h/2,0.12)});
    s.addText(text,{x,y,w,h,fontSize:fs,color:fg,bold,align:"center",valign:"middle",fontFace:F.body,margin:0});
  }
  const TH=(t)=>({text:t,options:{fill:{color:C.dark},color:C.white,bold:true,fontSize:9.5,align:"left",valign:"middle",fontFace:F.head}});
  const TC=(t,o={})=>({text:t,options:{fontSize:o.fs||8.6,color:o.color||C.ink2,align:o.align||"left",valign:"middle",fontFace:F.body,bold:o.bold||false,fill:{color:o.fill||C.white}}});

  // ============ PAGE 1 — 问题 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"SpeakerMem-R1 · 问题导向汇报 V2","问题：多人对话里，AI 分不清「谁说了什么」",C.amber);
    card(s,M,1.5,W-2*M,0.92,{fill:C.dark,shadow:true,lineCol:null});
    s.addImage({data:IC.target[C.amber],x:M+0.24,y:1.74,w:0.44,h:0.44});
    s.addText([
      {text:"要解决的问题：",options:{bold:true,color:C.amber}},
      {text:"为多方对话（3+ 人 / 群聊）设计可学习的、说话人锚定的记忆管理 —— 让 AI 正确地把每条信息归属到「正确的人、时间、受众」并据此作答。这是企业群聊 / 教育 / 医疗 / 客服的刚需，而现有系统集体失败。",options:{color:"DDE6F5"}},
    ],{x:M+0.84,y:1.5,w:W-2*M-1.05,h:0.92,fontSize:11,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.1});

    s.addText("现有系统集体失败（硬数据）",{x:M,y:2.66,w:8,h:0.26,fontSize:11,bold:true,color:C.muted,fontFace:F.body,margin:0});
    const stats=[
      ["0.12–0.18","SocialMemBench","开源记忆系统（Mem0/LangMem/Graphiti/Cognee）≈「没有记忆」",C.red],
      ["46%","GroupMemBench","最强系统上限；连 BM25 都能追平 → 结构性缺陷",C.amber],
      ["~26%","EverMemBench","即便给 Oracle 证据，多跳归因也只有这么多",C.red],
    ];
    const sw=(W-2*M-2*0.3)/3;
    stats.forEach((st,i)=>{
      const x=M+i*(sw+0.3),y=2.96,h=1.18;
      card(s,x,y,sw,h,{accent:st[3]});
      s.addText(st[0],{x:x+0.16,y:y+0.1,w:sw-0.3,h:0.5,fontSize:30,bold:true,color:st[3],fontFace:F.num,margin:0,valign:"middle"});
      s.addText(st[1],{x:x+0.16,y:y+0.62,w:sw-0.3,h:0.24,fontSize:10.5,bold:true,color:C.ink,fontFace:F.head,margin:0});
      s.addText(st[2],{x:x+0.16,y:y+0.86,w:sw-0.32,h:0.3,fontSize:8,color:C.muted,fontFace:F.body,margin:0,lineSpacingMultiple:1.02});
    });

    card(s,M,4.38,W-2*M,0.54,{fill:C.amberBg,accent:C.amber,lineCol:null});
    s.addText([
      {text:"本质：",options:{bold:true,color:C.amberDk}},
      {text:"现有记忆抹掉了 speaker- / audience-grounded 结构线索。多方比 dyadic 多三个挑战 —— ① 说话人归属  ② 受众适配  ③ 跨说话人隐私。",options:{color:C.ink2}},
    ],{x:M+0.18,y:4.38,w:W-2*M-0.34,h:0.54,fontSize:9.5,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.04});
    footer(s);
  }

  // ============ PAGE 2 — benchmark + 指标 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"现有 benchmark 与指标","拿什么衡量：三个多方 benchmark + 关键指标",C.cyan);
    const rows=[
      [TH("多方 Benchmark"),TH("规模 / 维度"),TH("报告指标"),TH("关键数字")],
      [TC("GroupMemBench",{bold:true,color:C.ink}),TC("图驱动合成 · 群组动态/归属/受众"),TC("EM · F1 · attribution acc"),TC("最强 46%；BM25 追平",{color:C.red,bold:true})],
      [TC("EverMemBench",{bold:true,color:C.ink,fill:C.panel2}),TC("每实例 1M+ token · 2,400 QA",{fill:C.panel2}),TC("Recall@K · F1",{fill:C.panel2}),TC("Oracle 多跳归因 ~26%",{color:C.red,bold:true,fill:C.panel2})],
      [TC("SocialMemBench",{bold:true,color:C.ink}),TC("430 personas · 5 类失败模式"),TC("per-category acc"),TC("开源 0.12–0.18；目标 >0.35",{color:C.red,bold:true})],
    ];
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[1.95,3.0,2.4,1.65],rowH:[0.34,0.52,0.52,0.52],border:{type:"solid",color:C.line,pt:0.75},valign:"middle",margin:[2,5,2,5],autoPage:false});

    s.addText([{text:"dyadic 对照（证明 N=1 不退化）：",options:{bold:true,color:C.ink2}},{text:" LoCoMo · LongMemEval · PersonaMem",options:{color:C.muted}}],{x:M,y:3.44,w:W-2*M,h:0.26,fontSize:9.5,italic:true,fontFace:F.body,margin:0});

    s.addText("核心指标",{x:M,y:3.78,w:8,h:0.24,fontSize:10.5,bold:true,color:C.muted,fontFace:F.body,margin:0});
    const mets=["Speaker attribution F1（核心）","QA token-F1 / EM","per-category acc（5 失败模式）","cross-speaker leakage rate（新增）","LoCoMo F1（兼容性）","context efficiency（2k≈32k, 16×）"];
    const mw=(W-2*M-2*0.2)/3;
    mets.forEach((m,i)=>{
      const col=i%3,row=Math.floor(i/3);
      const x=M+col*(mw+0.2),y=4.06+row*0.42;
      pill(s,x,y,mw,0.34,m,{bg:C.cyanBg,fg:C.cyanDk,fs:8.2});
    });
    card(s,M,4.92,0,0,{shadow:false,lineCol:null}); // noop spacer
    s.addText("⚠ 三个多方 benchmark 都没有训练集 → 训练数据须合成（已设计图驱动 pipeline，先合成 200 条）。",{x:M,y:4.95,w:W-2*M,h:0.26,fontSize:8.8,bold:true,color:C.amberDk,fontFace:F.body,margin:0});
    footer(s);
  }

  // ============ PAGE 3 — Related Work ①a：单用户记忆系统（training-free，按时间）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"Related Work ① · 单用户记忆系统（training-free）","按时间：解决什么 · 怎么做 · 自身还差什么",C.cyan);
    const fs=8.2;
    const rows=[
      [TH("工作"),TH("时间"),TH("解决的问题（动机）"),TH("方法简述"),TH("仍然不足")],
      [TC("MemoryBank",{bold:true,color:C.ink,fs}),TC("2023",{align:"center",fs}),TC("长期个性化 + 该不该遗忘",{fs}),TC("艾宾浩斯遗忘曲线 + 渐进 profile",{fs}),TC("规则无学习·事实回忆弱",{fs})],
      [TC("A-MEM",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2025.02",{align:"center",fs,fill:C.panel2}),TC("灵活关联、免预定义 schema",{fs,fill:C.panel2}),TC("原子卡片 + LLM 动态链接",{fs,fill:C.panel2}),TC("链接启发式·略弱于 Mem0",{fs,fill:C.panel2})],
      [TC("Mem0 / Mem0g",{bold:true,color:C.ink,fs}),TC("2025.04",{align:"center",fs}),TC("production 记忆、免塞全历史",{fs}),TC("LLM 决 ADD/UPDATE/DELETE(+图)",{fs}),TC("规则不可学·每 fact 一调用",{fs})],
      [TC("MemGAS",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2025.05",{align:"center",fs,fill:C.panel2}),TC("多粒度关联与检索权重",{fs,fill:C.panel2}),TC("多粒度 + GMM 聚类 + 熵路由",{fs,fill:C.panel2}),TC("构建开销大·不学习",{fs,fill:C.panel2})],
      [TC("MemoryOS",{bold:true,color:C.ink,fs}),TC("2025.06",{align:"center",fs}),TC("长期记忆的存储调度",{fs}),TC("OS 式短/中/长期分层 + 分页",{fs}),TC("调度启发式·阈值手工",{fs})],
      [TC("LightMem",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2025.10",{align:"center",fs,fill:C.panel2}),TC("记忆系统效率",{fs,fill:C.panel2}),TC("在线/离线分离 + 压缩 + 分段",{fs,fill:C.panel2}),TC("压缩丢细节·离线延迟",{fs,fill:C.panel2})],
      [TC("GAM",{bold:true,color:C.ink,fs}),TC("2025.11",{align:"center",fs}),TC("long-context agentic memory",{fs}),TC("Memorizer+Researcher 双 LLM + JIT",{fs}),TC("双 LLM 成本高",{fs})],
    ];
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[1.35,0.7,2.2,2.85,1.9],rowH:[0.3,0.46,0.46,0.46,0.46,0.46,0.46,0.46],border:{type:"solid",color:C.line,pt:0.5},valign:"middle",margin:[2,4,2,4],autoPage:false});
    footer(s);
  }

  // ============ PAGE 4 — Related Work ①b：RL 记忆方法（按时间）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"Related Work ① · RL 记忆方法（按时间）","解决什么 · 怎么做 · 自身还差什么",C.cyan);
    const fs=7.7;
    const rows=[
      [TH("工作"),TH("时间"),TH("解决的问题（动机）"),TH("方法简述"),TH("仍然不足")],
      [TC("MemAgent",{bold:true,color:C.ink,fs}),TC("2025",{align:"center",fs}),TC("超长文档 QA 线性复杂度",{fs}),TC("chunk 覆盖式定长记忆 + Multi-Conv DAPO",{fs}),TC("定长丢细节·重写贵",{fs})],
      [TC("Memory-R1",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2025.08",{align:"center",fs,fill:C.panel2}),TC("学记忆写操作",{fs,fill:C.panel2}),TC("双 agent + 记忆蒸馏",{fs,fill:C.panel2}),TC("动作仅 4 类·颗粒粗",{fs,fill:C.panel2})],
      [TC("AgeMem",{bold:true,color:C.ink,fs}),TC("2026.01",{align:"center",fs}),TC("LTM/STM 轨迹碎片化",{fs}),TC("step-wise GRPO · 6 工具动作",{fs}),TC("检索简单·credit 不精",{fs})],
      [TC("Mem-α",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2026.01",{align:"center",fs,fill:C.panel2}),TC("分层 + 超长泛化",{fs,fill:C.panel2}),TC("三组件(core/epi/sem)",{fs,fill:C.panel2}),TC("分层固定·边界启发式",{fs,fill:C.panel2})],
      [TC("Mem-T / TreeMem",{bold:true,color:C.ink,fs}),TC("2026.01–05",{align:"center",fs}),TC("稀疏奖励 / 无标注信用",{fs}),TC("树状信用：MoT 反传 / 依赖树+互信息",{fs}),TC("树搜索·检索依赖 开销",{fs})],
      [TC("CoMAM",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2026.03",{align:"center",fs,fill:C.panel2}),TC("sequential 忽视协同",{fs,fill:C.panel2}),TC("joint RL + rank credit",{fs,fill:C.panel2}),TC("joint 复杂·相关非因果",{fs,fill:C.panel2})],
      [TC("DeltaMem",{bold:true,color:C.ink,fs}),TC("2026.04",{align:"center",fs}),TC("奖励稀疏收敛慢",{fs}),TC("Levenshtein 稠密过程奖励(OT)",{fs}),TC("需 GT 标注·定位粗",{fs})],
      [TC("Memory-R2",{bold:true,color:C.ink,fs,fill:C.panel2}),TC("2026.05",{align:"center",fs,fill:C.panel2}),TC("multi-session 信用不公",{fs,fill:C.panel2}),TC("LoGo 共享态 rerollout + 课程",{fs,fill:C.panel2}),TC("增计算·只到 session 级",{fs,fill:C.panel2})],
      [TC("读侧 / 其他（5 篇）",{bold:true,color:C.muted,fs}),TC("25–26",{align:"center",fs}),TC("检索 / 蒸馏 / 记忆组织",{fs}),TC("R²-Mem 反思 · DeferMem 蒸馏 · DualMem 双流 · MemBuilder",{fs}),TC("多为读侧·增成本",{fs})],
    ];
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[1.45,0.78,2.1,2.8,1.87],rowH:[0.3,0.34,0.34,0.34,0.34,0.34,0.34,0.34,0.34,0.34],border:{type:"solid",color:C.line,pt:0.5},valign:"middle",margin:[2,4,2,4],autoPage:false});
    card(s,M,4.96,W-2*M,0.3,{fill:C.amberBg,accent:C.amber,lineCol:null});
    s.addText([{text:"统一总结：",options:{bold:true,color:C.amberDk}},{text:"以上工作全部为 dyadic / 单用户 —— 记忆不区分说话人。这正是 SpeakerMem-R1 切入的空白。",options:{color:C.ink2}}],{x:M+0.18,y:4.96,w:W-2*M-0.34,h:0.3,fontSize:8.4,fontFace:F.body,margin:0,valign:"middle"});
    footer(s);
  }

  // ============ PAGE 4 — Related Work ② + 空白 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"Related Work ② · 多方系统都不可学","多方工作全是 training-free / 仅评测 → 空白",C.amber);
    const rows=[
      [TH("工作"),TH("解决的问题"),TH("还有什么不足")],
      [TC("Collaborative Mem",{bold:true,color:C.ink}),TC("多用户共享/私有 + 访问控制"),TC("写入是固定规则，不可学习")],
      [TC("G-Memory",{bold:true,color:C.ink,fill:C.panel2}),TC("多 agent 三层图记忆 (+20.89%)",{fill:C.panel2}),TC("training-free · 面向 AI-agent · 不可学",{fill:C.panel2})],
      [TC("SA-LLM / MuPaS",{bold:true,color:C.ink}),TC("多方对话生成 / role-mask 训练"),TC("针对生成，非记忆管理 · 无 RL")],
      [TC("GroupMem / Social / Ever",{bold:true,color:C.ink,fill:C.panel2}),TC("多方记忆评测（揭示失败）",{fill:C.panel2}),TC("纯评测集 · 无训练集",{fill:C.panel2})],
    ];
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[2.5,3.2,3.3],rowH:[0.3,0.46,0.46,0.46,0.46],border:{type:"solid",color:C.line,pt:0.5},valign:"middle",margin:[2,5,2,5],autoPage:false});

    card(s,M,3.74,W-2*M,1.18,{fill:C.dark,shadow:true,lineCol:null});
    s.addText([{text:"空白确认：",options:{bold:true,color:C.amber}},{text:"多方 × RL 记忆 = 零篇先例（4 轮检索验证）。",options:{color:C.white,bold:true}}],{x:M+0.24,y:3.86,w:W-2*M-0.48,h:0.3,fontSize:13,fontFace:F.head,margin:0});
    const gaps=[["users","Action 无 speaker_id","多方发言压成 user，丢归属"],["scale","Reward 盲区","整体内容对、归属错仍高分"],["diagram","Credit 盲区","speaker 分布不同，奖励不可比"]];
    const gw=(W-2*M-0.48-2*0.24)/3;
    gaps.forEach((g,i)=>{
      const x=M+0.24+i*(gw+0.24),y=4.24;
      s.addImage({data:IC[g[0]][C.amber],x:x,y:y+0.02,w:0.24,h:0.24});
      s.addText(g[1],{x:x+0.3,y:y-0.04,w:gw-0.3,h:0.26,fontSize:9.5,bold:true,color:C.amber,fontFace:F.head,margin:0,valign:"middle"});
      s.addText(g[2],{x:x+0.02,y:y+0.26,w:gw,h:0.34,fontSize:7.8,color:"C7D0E8",fontFace:F.body,margin:0,lineSpacingMultiple:1.02});
    });
    footer(s);
  }

  // ============ PAGE 5 — 方法（简）+ 指标 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"方法（次要）+ 评测指标","三个贡献分别修三个盲点；指标看右栏",C.cyan);
    const lx=M,lw=5.5,ly=1.55;
    const cons=[
      ["scale",C.cyan,"① SpeakerLevenshtein 奖励","按说话人分桶稠密奖励（扩展 DeltaMem）→ 修 Reward 盲区"],
      ["diagram",C.violet,"② SC-LoGo-GRPO","按 active speaker set 分层 rerollout（扩展 Memory-R2）→ 修 Credit 盲区"],
      ["layers",C.amber,"③ 5 层 Speaker-Indexed Memory","per-speaker + group，对应 5 类失败模式 → 修 Action/结构 盲区"],
    ];
    cons.forEach((c,i)=>{
      const y=ly+i*1.06,h=0.94;
      card(s,lx,y,lw,h,{accent:c[1]});
      s.addImage({data:IC[c[0]][c[1]],x:lx+0.2,y:y+0.22,w:0.5,h:0.5});
      s.addText(c[2],{x:lx+0.86,y:y+0.14,w:lw-1.0,h:0.3,fontSize:12,bold:true,color:C.ink,fontFace:F.head,margin:0});
      s.addText(c[3],{x:lx+0.86,y:y+0.46,w:lw-1.04,h:0.42,fontSize:9,color:C.ink2,fontFace:F.body,margin:0,lineSpacingMultiple:1.04});
    });

    const rx=lx+lw+0.3,rw=W-M-rx;
    card(s,rx,ly,rw,3.18,{fill:C.dark,shadow:true,lineCol:null});
    s.addText("我们报告的指标",{x:rx+0.22,y:ly+0.18,w:rw-0.4,h:0.3,fontSize:12,bold:true,color:C.white,fontFace:F.head,margin:0});
    const mets=[["Speaker attribution F1","核心：归属准不准"],["QA token-F1 / EM","最终答对没"],["per-category acc","5 类失败模式分项"],["leakage rate","跨说话人泄漏（新维度）"],["LoCoMo F1","dyadic 不退化"]];
    mets.forEach((m,i)=>{
      const y=ly+0.58+i*0.5;
      s.addShape(OVAL,{x:rx+0.24,y:y+0.04,w:0.12,h:0.12,fill:{color:C.cyan},line:{type:"none"}});
      s.addText(m[0],{x:rx+0.44,y:y-0.04,w:rw-0.62,h:0.24,fontSize:9.8,bold:true,color:C.cyan,fontFace:F.head,margin:0});
      s.addText(m[1],{x:rx+0.44,y:y+0.18,w:rw-0.62,h:0.22,fontSize:8,color:"C7D0E8",fontFace:F.body,margin:0});
    });
    footer(s);
  }

  // ============ PAGE 6 — 预期 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"预期结果与贡献","目标数字 + 关键消融 + 贡献",C.cyan);
    const tg=[
      [C.red,"SocialMemBench","目标 > 0.35","开源系统仅 0.12–0.18"],
      [C.amber,"GroupMemBench","超过最强 46%","attribution 类显著提升"],
      [C.green,"LoCoMo","≈ 49.67","证明 dyadic 不退化"],
    ];
    const tw=(W-2*M-2*0.3)/3;
    tg.forEach((t,i)=>{
      const x=M+i*(tw+0.3),y=1.55,h=1.2;
      card(s,x,y,tw,h,{accent:t[0]});
      s.addText(t[1],{x:x+0.16,y:y+0.12,w:tw-0.3,h:0.26,fontSize:10.5,bold:true,color:C.ink,fontFace:F.head,margin:0});
      s.addText(t[2],{x:x+0.16,y:y+0.4,w:tw-0.3,h:0.4,fontSize:18,bold:true,color:t[0],fontFace:F.num,margin:0,valign:"middle"});
      s.addText(t[3],{x:x+0.16,y:y+0.86,w:tw-0.3,h:0.28,fontSize:8.2,color:C.muted,fontFace:F.body,margin:0});
    });

    card(s,M,2.95,W-2*M,0.78,{fill:C.panel2,shadow:false});
    s.addText("关键消融（验证每个贡献的增量）",{x:M+0.2,y:3.02,w:8,h:0.26,fontSize:10,bold:true,color:C.ink,fontFace:F.head,margin:0});
    s.addText([
      {text:"per-speaker vs flat Levenshtein ",options:{color:C.ink2}},{text:"+5–10 F1",options:{bold:true,color:C.cyanDk}},
      {text:"    ·    joint vs sequential ",options:{color:C.ink2}},{text:"+4–8",options:{bold:true,color:C.violet}},
      {text:"    ·    LoGo vs 无 ",options:{color:C.ink2}},{text:"+2–4",options:{bold:true,color:C.amberDk}},
    ],{x:M+0.2,y:3.32,w:W-2*M-0.4,h:0.34,fontSize:10,fontFace:F.body,margin:0,valign:"middle"});

    card(s,M,3.92,W-2*M,1.0,{fill:C.dark,shadow:true,lineCol:null});
    s.addText("贡献",{x:M+0.24,y:3.99,w:3,h:0.28,fontSize:12,bold:true,color:C.amber,fontFace:F.head,margin:0});
    const ctr=["首个多方对话 RL 记忆方法（零篇先例）","三大技术贡献：奖励 / 信用分配 / 记忆结构","新评测维度：跨说话人隐私泄漏","开源代码 + 合成多方数据集"];
    ctr.forEach((t,i)=>{
      const col=i%2,row=Math.floor(i/2);
      const x=M+0.24+col*4.5,y=4.3+row*0.32;
      s.addImage({data:IC.check[C.cyan],x:x,y:y+0.02,w:0.18,h:0.18});
      s.addText(t,{x:x+0.26,y:y-0.03,w:4.2,h:0.28,fontSize:9.2,color:"DDE6F5",fontFace:F.body,margin:0,valign:"middle"});
    });
    footer(s);
  }

  // ============ PAGE 8 — 值得先复现（实验规划）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"实验规划 · 我的判断（供老师指正）","值得先复现的 work —— 按优先级",C.cyan);
    const tiers=[
      [C.green,"① 立刻做","低成本 · 必报 baseline",[
        ["Mem0","开源 · 跑通 = 验证评测 pipeline + 拿对照数字"],
        ["BM25","几行 · 坐实「BM25 追平」motivation"],
      ]],
      [C.cyan,"② RL 脚手架","有开源代码可 fork",[
        ["MemAgent","fork → per-speaker 多流，最省力 RL 起点"],
        ["LightMem（可选）","强近期 training-free 对照"],
      ]],
      [C.amber,"③ 核心前身","无代码 · 须自实现",[
        ["DeltaMem 奖励","贡献① 基础，先单独验证能分好坏"],
        ["Memory-R2 co-learn","贡献②；先 fact-extractor（命脉），LoGo 次之"],
        ["Memory-R1","outcome-only RL baseline（对照）"],
      ]],
    ];
    const cw=(W-2*M-2*0.3)/3, y0=1.55, h=2.62;
    tiers.forEach((t,i)=>{
      const x=M+i*(cw+0.3);
      card(s,x,y0,cw,h,{shadow:true});
      s.addShape(RECT,{x,y:y0,w:cw,h:0.46,fill:{color:t[0]}});
      s.addText(t[1],{x:x+0.16,y:y0,w:cw-0.3,h:0.46,fontSize:13,bold:true,color:C.white,valign:"middle",fontFace:F.head,margin:0});
      s.addText(t[2],{x:x+0.16,y:y0+0.52,w:cw-0.3,h:0.24,fontSize:8.5,bold:true,color:t[0],fontFace:F.body,margin:0});
      t[3].forEach((w,k)=>{
        const wy=y0+0.84+k*0.6;
        s.addShape(OVAL,{x:x+0.16,y:wy+0.02,w:0.12,h:0.12,fill:{color:t[0]},line:{type:"none"}});
        s.addText(w[0],{x:x+0.34,y:wy-0.05,w:cw-0.48,h:0.24,fontSize:9.8,bold:true,color:C.ink,fontFace:F.head,margin:0});
        s.addText(w[1],{x:x+0.34,y:wy+0.19,w:cw-0.5,h:0.4,fontSize:7.6,color:C.muted,fontFace:F.body,margin:0,lineSpacingMultiple:1.02});
      });
    });
    card(s,M,4.34,W-2*M,0.6,{fill:C.dark,accent:C.cyan,lineCol:null});
    s.addText([
      {text:"我的判断：",options:{bold:true,color:C.cyan}},
      {text:"Mem0+BM25 坐实 benchmark / motivation → fork MemAgent 拿能训的 RL loop → 自实现 DeltaMem 奖励 + Memory-R2 的 fact-extractor。",options:{color:"DDE6F5"}},
      {text:" 暂不优先：CoMAM / Mem-T / TreeMem / MemoryOS（cite 即可）。",options:{color:C.faint}},
    ],{x:M+0.2,y:4.34,w:W-2*M-0.4,h:0.6,fontSize:8.8,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.06});
    footer(s);
  }

  // ============ PAGE 9 — 附录 · case 速览 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"附录 A · 核心能力 case 速览","6 类「谁说了什么」难题（跨领域）",C.violet);
    const ex=[
      [C.cyan,"① 单流混淆","Alice:训练·Bob:数据·Carol:评测","谁评测?→Carol","企业协作"],
      [C.violet,"② 跨说话人引用","Alice:「Bob 想换工作」","Bob 想换?→是(Alice 转述)","客服/合规"],
      [C.amber,"③ 同类实体不合并","Alice:我妈住院·Carol:我妈退休","Carol 妈?→退休","医疗/教育"],
      [C.green,"④ 冲突信念按人分","Alice 挺 PyTorch·Bob 坚持 JAX","Bob 倾向?→JAX","决策/多agent"],
      [C.cyanDk,"⑤ per-speaker 时序","Alice:A 司→(T20)跳 B 司","现在?→B(之前 A)","CRM/陪伴"],
      [C.red,"⑥ 群体vs个体+隐私","群:Slack·Alice 私下爱飞书·在看机会","项目?→Slack；Carol 问→不泄漏","社交/合规"],
    ];
    const cw=(W-2*M-2*0.28)/3,ch=1.46;
    ex.forEach((e,i)=>{
      const col=i%3,row=Math.floor(i/3);
      const x=M+col*(cw+0.28),y=1.54+row*(ch+0.16);
      card(s,x,y,cw,ch,{accent:e[0]});
      s.addText(e[1],{x:x+0.16,y:y+0.1,w:cw-0.3,h:0.28,fontSize:10.5,bold:true,color:e[0],fontFace:F.head,margin:0});
      s.addText(e[2],{x:x+0.16,y:y+0.42,w:cw-0.3,h:0.36,fontSize:8,color:C.ink2,fontFace:F.body,margin:0,valign:"top",lineSpacingMultiple:1.05});
      card(s,x+0.16,y+ch-0.5,cw-0.32,0.3,{fill:C.panel,shadow:false,lineCol:null});
      s.addText([{text:"Q ",options:{bold:true,color:e[0]}},{text:e[3],options:{bold:true,color:C.ink}}],{x:x+0.26,y:y+ch-0.5,w:cw-0.48,h:0.3,fontSize:7.4,fontFace:F.body,margin:0,valign:"middle"});
      s.addText(e[4],{x:x+0.16,y:y+ch-0.18,w:cw-0.3,h:0.18,fontSize:7,italic:true,color:C.muted,fontFace:F.body,margin:0});
    });
    footer(s);
  }

  // ============ PAGE 8 — 附录 · 典型 case 详解 ============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"附录 B · 典型 case 详解","两个例子：现有系统为何错、我们怎么对",C.violet);
    const cases=[
      {accent:C.cyan,type:"① 单流混淆",chat:[["A","Alice","模型训练我来"],["B","Bob","数据清洗交给我"],["C","Carol","我盯评测"]],qa:"谁负责评测? → Carol",bad:"现有系统压成一条 user，分工糊成一团，问归属只能猜。",ours:"speaker_id 动作 + per_speaker_core + 分桶奖励 → 每条事实锚定到人。"},
      {accent:C.amber,type:"③ 同类实体不合并",chat:[["张","张医生","我患者血糖高"],["李","李医生","我接术后感染"],["王","王医生","我患者心率不齐"]],qa:"李医生的患者? → 术后感染",bad:"多人都谈「我的患者」，同类实体易被合并；规模越大越糊。",ours:"唯一 s_owner + per-speaker 分层，结构上禁止跨人 merge。"},
    ];
    const cw=(W-2*M-0.3)/2;
    cases.forEach((c,ci)=>{
      const x=M+ci*(cw+0.3),y0=1.55;
      s.addText(c.type,{x:x,y:y0,w:cw,h:0.28,fontSize:12,bold:true,color:c.accent,fontFace:F.head,margin:0});
      const cols=[C.cyan,C.amber,C.violet];
      c.chat.forEach((b,k)=>{
        const y=y0+0.36+k*0.5;
        s.addShape(OVAL,{x:x,y:y,w:0.34,h:0.34,fill:{color:cols[k%3]},line:{type:"none"}});
        s.addText(b[0],{x:x,y:y,w:0.34,h:0.34,fontSize:10,bold:true,color:C.white,align:"center",valign:"middle",fontFace:F.head,margin:0});
        s.addShape(ROUND,{x:x+0.44,y:y-0.01,w:cw-0.44,h:0.4,fill:{color:C.panel2},line:{color:C.line,width:0.5},rectRadius:0.05});
        s.addText([{text:b[1]+"：",options:{bold:true,color:cols[k%3]}},{text:b[2],options:{color:C.ink2}}],{x:x+0.56,y:y-0.01,w:cw-0.66,h:0.4,fontSize:8.5,fontFace:F.body,margin:0,valign:"middle"});
      });
      card(s,x,y0+1.92,cw,0.36,{fill:C.dark,shadow:false,lineCol:null});
      s.addText([{text:"Q ",options:{bold:true,color:c.accent}},{text:c.qa,options:{bold:true,color:C.cyan}}],{x:x+0.16,y:y0+1.92,w:cw-0.3,h:0.36,fontSize:8.8,fontFace:F.body,margin:0,valign:"middle"});
      card(s,x,y0+2.4,cw,0.46,{accent:C.red,fill:C.redBg,lineCol:null});
      s.addText([{text:"难点：",options:{bold:true,color:C.red}},{text:c.bad,options:{color:C.ink2}}],{x:x+0.16,y:y0+2.4,w:cw-0.3,h:0.46,fontSize:8,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.02});
      card(s,x,y0+2.96,cw,0.46,{accent:C.cyan,fill:C.cyanBg,lineCol:null});
      s.addText([{text:"我们：",options:{bold:true,color:C.cyanDk}},{text:c.ours,options:{color:C.ink2}}],{x:x+0.16,y:y0+2.96,w:cw-0.3,h:0.46,fontSize:8,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.02});
    });
    footer(s);
  }

  // ============ PAGE 9 — 附录 · 方法/训练（怎么做 备查）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"附录 C · 方法 / 训练（备查）","系统数据流 + 三阶段训练",C.violet);
    const boxes=[[C.cyan,"A_mem 写记忆","新发言→记忆动作"],[C.violet,"M 5 层记忆","按说话人分桶"],[C.amber,"A_ret 检索","可访问+相关"],[C.green,"A_ans 回答","适配提问者"]];
    const bw=1.95,gap=0.37,by=1.6,bh=1.0;
    boxes.forEach((b,i)=>{
      const x=M+i*(bw+gap);
      card(s,x,by,bw,bh,{shadow:true});
      s.addShape(RECT,{x,y:by,w:bw,h:0.36,fill:{color:b[0]}});
      s.addText(b[1],{x:x+0.12,y:by,w:bw-0.2,h:0.36,fontSize:10,bold:true,color:C.white,valign:"middle",fontFace:F.head,margin:0});
      s.addText(b[2],{x:x+0.14,y:by+0.46,w:bw-0.26,h:0.46,fontSize:8.2,color:C.ink2,fontFace:F.body,margin:0,valign:"top"});
      if(i<3) s.addImage({data:IC.arrow[C.faint],x:x+bw+0.04,y:by+0.36,w:0.29,h:0.26});
    });

    s.addText("三阶段训练",{x:M,y:2.92,w:8,h:0.26,fontSize:11,bold:true,color:C.muted,fontFace:F.body,margin:0});
    const stg=[[C.cyan,"Stage 1 · SFT 热启动","role-masked SFT；attribution F1>50%"],[C.violet,"Stage 2 · Joint RL","SpeakerMem-GRPO；K=3→5→8 课程"],[C.amber,"Stage 3 · 端到端","三 benchmark 混合，回填指标"]];
    const sw=(W-2*M-2*0.3)/3;
    stg.forEach((g,i)=>{
      const x=M+i*(sw+0.3),y=3.22,h=0.92;
      card(s,x,y,sw,h,{accent:g[0]});
      s.addText(g[1],{x:x+0.16,y:y+0.12,w:sw-0.3,h:0.28,fontSize:10.5,bold:true,color:g[0],fontFace:F.head,margin:0});
      s.addText(g[2],{x:x+0.16,y:y+0.42,w:sw-0.3,h:0.42,fontSize:8.3,color:C.ink2,fontFace:F.body,margin:0,lineSpacingMultiple:1.04});
    });
    card(s,M,4.4,W-2*M,0.5,{fill:C.dark,accent:C.cyan,lineCol:null});
    s.addText([{text:"奖励 ",options:{bold:true,color:C.cyan}},{text:"R = 0.5·R_task + 0.8·R_state + 0.3·R_attr + 0.2·R_aud + …  ",options:{color:"DDE6F5",fontFace:"Consolas"}},{text:"（R_state 稠密、按说话人分桶，主导）",options:{color:C.faint}}],{x:M+0.2,y:4.4,w:W-2*M-0.4,h:0.5,fontSize:9,fontFace:F.body,margin:0,valign:"middle"});
    footer(s);
  }

  // ============ PAGE 12 — P4 复现进度（BM25 实测）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"P4 · 复现进度（DeepSeek 实测，2026-06-09）","BM25 三数据集全量：连关键词检索都很能打",C.green);
    const C0=(t,o={})=>TC(t,{align:"center",...o});
    const rows=[
      [TH("Benchmark"),TH("题数"),TH("BM25 acc"),TH("Mem0 acc"),TH("BM25 EM/F1"),TH("关键发现")],
      [TC("GroupMemBench",{bold:true,color:C.ink}),C0("745"),C0("44.6%",{bold:true,color:C.cyanDk}),C0("跑ing",{color:C.muted}),C0("13.8 / 25.0"),TC("≈ 追平论文最强 46%",{color:C.red,bold:true})],
      [TC("SocialMemBench",{bold:true,color:C.ink,fill:C.panel2}),C0("1031",{fill:C.panel2}),C0("28.6%",{bold:true,color:C.cyanDk,fill:C.panel2}),C0("13.7%",{bold:true,color:C.amberDk,fill:C.panel2}),C0("3.6 / 15.7",{fill:C.panel2}),TC("BM25 完胜 Mem0；Mem0∈0.12–0.18",{color:C.red,bold:true,fill:C.panel2})],
      [TC("EverMemBench",{bold:true,color:C.ink}),C0("2400"),C0("52.5%",{bold:true,color:C.cyanDk}),C0("跑ing",{color:C.muted}),C0("4.8 / 9.9"),TC("MC 64% / 开放式 27%(≈oracle)",{color:C.ink2})],
    ];
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[1.85,0.7,1.15,1.15,1.35,2.8],rowH:[0.34,0.5,0.5,0.5],border:{type:"solid",color:C.line,pt:0.75},valign:"middle",margin:[2,5,2,5],autoPage:false});
    s.addText("指标统一：bench_loaders 归一化为同一 schema(多选拼进问题)，judge acc(主)/EM/F1/per-category 一套代码通吃；agent+judge 均 DeepSeek，16 并发；Mem0=并行无合并变体。详见下一页按类别表。",
      {x:M,y:3.55,w:W-2*M,h:0.4,fontSize:8.3,italic:true,color:C.muted,fontFace:F.body,margin:0,lineSpacingMultiple:1.05});
    card(s,M,4.05,W-2*M,0.86,{fill:C.amberBg,accent:C.amber,lineCol:null});
    s.addText([
      {text:"motivation 坐实：",options:{bold:true,color:C.amberDk}},
      {text:"BM25 单凭关键词就追平/超过现有记忆系统 → 现有系统在多方场景把 speaker-/audience-grounded 结构线索抹掉了。",options:{color:C.ink2}},
      {text:" Mem0 全量(并行抽取)对比进行中。",options:{color:C.muted}},
    ],{x:M+0.2,y:4.05,w:W-2*M-0.4,h:0.86,fontSize:9.5,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.1});
    footer(s);
  }

  // ============ PAGE 13 — SocialMemBench 按类别 BM25 vs Mem0（详细）============
  {
    const s=pres.addSlide(); s.background={color:C.white};
    header(s,"P4 · 详细结果（SocialMemBench 1031 题）","按 9 类拆：BM25 几乎全面压过 Mem0",C.green);
    const C0=(t,o={})=>TC(t,{align:"center",fs:8.4,...o});
    const D=[ // 类别, BM25 acc, Mem0 acc, BM25 F1, Mem0 F1, 大差距?
      ["Q1 单人召回","25.3","20.9","13.8","12.0",false],
      ["Q2 群体决策","24.7","14.8","10.3","7.4",false],
      ["Q3 多人聚合","4.5","4.5","12.1","15.8",false],
      ["Q4 归属探针","66.2","11.2","38.1","6.7",true],
      ["Q5 ToM 揣测","38.0","3.3","18.7","10.4",true],
      ["Q6 群规vs个人","25.9","25.9","14.5","12.3",false],
      ["Q7 关系边","29.8","9.4","15.7","10.7",true],
      ["Q8 时间漂移","20.6","12.2","12.2","10.4",false],
      ["Q9 离群成员","10.0","10.0","8.2","10.4",false],
    ];
    const rows=[[TH("类别(Q1–Q9)"),TH("BM25 acc"),TH("Mem0 acc"),TH("BM25 F1"),TH("Mem0 F1")]];
    D.forEach((r,i)=>{
      const bg=i%2?C.panel2:C.white;
      rows.push([TC(r[0],{bold:true,color:C.ink,fs:8.4,fill:bg}),
        C0(r[1]+"%",{bold:true,color:r[5]?C.red:C.cyanDk,fill:bg}),C0(r[2]+"%",{color:C.amberDk,fill:bg}),
        C0(r[3],{fill:bg}),C0(r[4],{fill:bg})]);
    });
    rows.push([TC("总体",{bold:true,color:C.white,fs:8.6,fill:C.dark}),
      C0("28.6%",{bold:true,color:C.white,fill:C.dark}),C0("13.7%",{bold:true,color:C.white,fill:C.dark}),
      C0("15.7",{color:C.white,fill:C.dark}),C0("10.5",{color:C.white,fill:C.dark})]);
    s.addTable(rows,{x:M,y:1.5,w:W-2*M,colW:[2.4,1.65,1.65,1.65,1.65],rowH:[0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.3,0.32],border:{type:"solid",color:C.line,pt:0.5},valign:"middle",margin:[1,4,1,4],autoPage:false});
    card(s,M,4.95,W-2*M,0.5,{fill:C.cyanBg,accent:C.cyan,lineCol:null});
    s.addText([{text:"看点：",options:{bold:true,color:C.cyanDk}},
      {text:"差距最大在 Q4 归属(66→11)、Q5 ToM(38→3)、Q7 关系(30→9) —— Mem0 有损抽取丢了精确归属/关系，正是 speaker-grounded 方法要补的。",options:{color:C.ink2}}],
      {x:M+0.2,y:4.95,w:W-2*M-0.4,h:0.5,fontSize:8.6,fontFace:F.body,margin:0,valign:"middle",lineSpacingMultiple:1.05});
    footer(s);
  }

  const out=process.argv[2]||"D:/ComputerScience/ZJUIDG/2026AAAI/SpeakerMem-R1-汇报V2-问题导向.pptx";
  await pres.writeFile({fileName:out});
  console.log("WROTE:",out);
}
main().catch(e=>{console.error(e);process.exit(1);});
