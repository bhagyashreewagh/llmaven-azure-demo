const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "LLMaven AI Usage Pipeline";

// Color palette (matches Streamlit dashboard)
const C = {
  bg:       "0F1117",  // near black
  card:     "1A1F2E",  // dark navy card
  border:   "2D3561",  // card border
  accent:   "64FFDA",  // teal green accent
  purple:   "7B61FF",  // purple
  pink:     "FF6B9D",  // pink
  yellow:   "FFD166",  // yellow
  white:    "FFFFFF",
  offwhite: "CCD6F6",  // light blue-white
  muted:    "8892B0",  // muted grey-blue
};

const makeShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.25 });

// ── Slide 1: Title ─────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  // Top accent bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }, line: { color: C.accent } });

  // Glowing circle behind brain icon
  s.addShape(pres.shapes.OVAL, {
    x: 4.5, y: 0.7, w: 1, h: 1,
    fill: { color: C.accent, transparency: 80 },
    line: { color: C.accent, width: 1 }
  });

  s.addText("LLMaven", {
    x: 0.5, y: 1.7, w: 9, h: 1.1,
    fontSize: 54, bold: true, color: C.white,
    fontFace: "Calibri", align: "center", margin: 0
  });

  s.addText("AI Usage Pipeline", {
    x: 0.5, y: 2.65, w: 9, h: 0.7,
    fontSize: 28, bold: false, color: C.accent,
    fontFace: "Calibri", align: "center", margin: 0
  });

  // Divider
  s.addShape(pres.shapes.RECTANGLE, {
    x: 3.5, y: 3.4, w: 3, h: 0.04,
    fill: { color: C.border }, line: { color: C.border }
  });

  s.addText("University of Washington  |  eScience Institute", {
    x: 0.5, y: 3.55, w: 9, h: 0.4,
    fontSize: 13, color: C.muted, fontFace: "Calibri", align: "center", margin: 0
  });

  s.addText("LiteLLM  |  Azure  |  Pulumi  |  Streamlit", {
    x: 0.5, y: 4.0, w: 9, h: 0.35,
    fontSize: 12, color: C.border, fontFace: "Calibri", align: "center", margin: 0
  });

  // Bottom bar
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 2: Current Architecture ─────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }, line: { color: C.accent } });

  s.addText("Current Pipeline Architecture", {
    x: 0.5, y: 0.2, w: 9, h: 0.55,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Pull-based batch pipeline  |  runs daily at midnight", {
    x: 0.5, y: 0.72, w: 9, h: 0.3,
    fontSize: 12, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Pipeline boxes
  const boxes = [
    { label: "LLMaven Server", sub: "LiteLLM + PostgreSQL", color: C.purple, icon: "SERVER" },
    { label: "Azure Functions", sub: "Extract + Clean daily", color: C.accent,  icon: "FUNC"   },
    { label: "Azure Data Lake", sub: "Raw JSONL + Parquet",  color: C.yellow,  icon: "LAKE"   },
    { label: "Streamlit Dashboard", sub: "Container Apps",    color: C.pink,    icon: "DASH"   },
  ];

  const bw = 1.9, bh = 1.1, startX = 0.3, y = 1.2, gap = 0.22;

  boxes.forEach((b, i) => {
    const x = startX + i * (bw + gap);

    // Card background
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: bw, h: bh,
      fill: { color: C.card },
      line: { color: b.color, width: 1.5 },
      shadow: makeShadow()
    });

    // Top accent bar on card
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: bw, h: 0.06,
      fill: { color: b.color }, line: { color: b.color }
    });

    s.addText(b.label, {
      x: x + 0.1, y: y + 0.12, w: bw - 0.2, h: 0.45,
      fontSize: 13, bold: true, color: C.white, fontFace: "Calibri",
      align: "center", margin: 0
    });
    s.addText(b.sub, {
      x: x + 0.1, y: y + 0.58, w: bw - 0.2, h: 0.35,
      fontSize: 10, color: C.muted, fontFace: "Calibri",
      align: "center", margin: 0
    });

    // Arrow between boxes
    if (i < boxes.length - 1) {
      const ax = x + bw + 0.04;
      s.addShape(pres.shapes.RECTANGLE, {
        x: ax, y: y + bh/2 - 0.02, w: gap - 0.08, h: 0.04,
        fill: { color: C.border }, line: { color: C.border }
      });
    }
  });

  // Resource details row
  const details = [
    { title: "Pulumi IaC", body: "All Azure resources defined as Python code. One command to deploy everything." },
    { title: "ADLS Gen2", body: "Hierarchical data lake. ~$0.018/GB/month. Partitioned by date for fast queries." },
    { title: "Parquet Format", body: "85% smaller than CSV. 10x faster to query. Columnar compression." },
    { title: "Container Apps", body: "Scales to zero when idle. ~$2-5/month. Public shareable URL." },
  ];

  const dw = 2.15, dy = 2.6;
  details.forEach((d, i) => {
    const x = 0.3 + i * (dw + 0.07);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: dy, w: dw, h: 1.3,
      fill: { color: "12172A" }, line: { color: C.border, width: 0.75 }
    });
    s.addText(d.title, {
      x: x + 0.1, y: dy + 0.1, w: dw - 0.2, h: 0.28,
      fontSize: 11, bold: true, color: C.accent, fontFace: "Calibri", margin: 0
    });
    s.addText(d.body, {
      x: x + 0.1, y: dy + 0.38, w: dw - 0.2, h: 0.82,
      fontSize: 9.5, color: C.offwhite, fontFace: "Calibri", margin: 0
    });
  });

  // Cost badge
  s.addShape(pres.shapes.RECTANGLE, {
    x: 3.5, y: 4.15, w: 3, h: 0.5,
    fill: { color: C.card }, line: { color: C.accent, width: 1 }
  });
  s.addText("Total estimated cost: ~$2-5 / month", {
    x: 3.5, y: 4.15, w: 3, h: 0.5,
    fontSize: 13, bold: true, color: C.accent, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 3: Dashboard Screenshot ─────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }, line: { color: C.accent } });

  s.addText("Live Dashboard", {
    x: 0.5, y: 0.15, w: 5.5, h: 0.5,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Built with Streamlit + Plotly  |  Hosted on Azure Container Apps", {
    x: 0.5, y: 0.62, w: 6.5, h: 0.28,
    fontSize: 11, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Dashboard screenshot
  const ssPath = path.join(__dirname, "dashboard_screenshot.png");
  if (fs.existsSync(ssPath)) {
    s.addImage({ path: ssPath, x: 0.3, y: 0.98, w: 9.4, h: 4.2, shadow: makeShadow() });
  }

  // Link badge
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.3, y: 5.1, w: 4.5, h: 0.38,
    fill: { color: C.card }, line: { color: C.accent, width: 1 }
  });
  s.addText("Live demo: http://localhost:8501   (Azure: coming soon)", {
    x: 0.3, y: 5.1, w: 4.5, h: 0.38,
    fontSize: 10, color: C.accent, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0
  });

  // Features list on right
  const features = ["Model usage breakdown", "Daily cost over time", "Token distribution (input vs output)", "Turns per session histogram", "Source filter (isolate coding activity)", "Top users by spend"];
  s.addText(features.map((f, i) => ({
    text: f,
    options: { bullet: true, breakLine: i < features.length - 1, fontSize: 10, color: C.offwhite }
  })), { x: 4.9, y: 5.0, w: 4.8, h: 0.55, margin: 0 });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 4: GitHub Repo ──────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.purple }, line: { color: C.purple } });

  s.addText("GitHub Repository", {
    x: 0.5, y: 0.18, w: 9, h: 0.5,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });

  // Repo URL box
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.82, w: 9, h: 0.52,
    fill: { color: C.card }, line: { color: C.purple, width: 1.5 }
  });
  s.addText("github.com/bhagyashreewagh/llmaven-azure-demo", {
    x: 0.5, y: 0.82, w: 9, h: 0.52,
    fontSize: 16, bold: true, color: C.accent, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
    hyperlink: { url: "https://github.com/bhagyashreewagh/llmaven-azure-demo" }
  });

  // Repo structure
  const files = [
    { name: "pulumi/", desc: "Pulumi Python IaC - all Azure resources in one file. Run 'pulumi up' to deploy.", color: C.accent },
    { name: "function_app/", desc: "Azure Function - daily timer trigger. Extracts JSONL, cleans to Parquet, uploads to Data Lake.", color: C.yellow },
    { name: "dashboard/", desc: "Streamlit app + Dockerfile. Charts for model usage, cost, tokens, sessions, source breakdown.", color: C.pink },
    { name: "azure_pipeline_resources.md", desc: "Full resource comparison guide with cost estimates per GB for every Azure service considered.", color: C.purple },
    { name: "research_survey.md", desc: "End-to-end researcher survey to understand how teams use AI coding assistants.", color: C.muted },
  ];

  const fw = 4.3, fh = 0.78, startY = 1.5;
  files.forEach((f, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.4 + col * (fw + 0.2);
    const y = startY + row * (fh + 0.12);

    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: fw, h: fh,
      fill: { color: "12172A" }, line: { color: f.color, width: 0.75 }
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 0.06, h: fh,
      fill: { color: f.color }, line: { color: f.color }
    });
    s.addText(f.name, {
      x: x + 0.15, y: y + 0.06, w: fw - 0.2, h: 0.25,
      fontSize: 11, bold: true, color: C.white, fontFace: "Calibri", margin: 0
    });
    s.addText(f.desc, {
      x: x + 0.15, y: y + 0.32, w: fw - 0.2, h: 0.42,
      fontSize: 9, color: C.muted, fontFace: "Calibri", margin: 0
    });
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 5: Research Questions ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.yellow }, line: { color: C.yellow } });

  s.addText("Research Questions", {
    x: 0.5, y: 0.15, w: 9, h: 0.5,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("What do we want to learn from the data?", {
    x: 0.5, y: 0.62, w: 9, h: 0.28,
    fontSize: 12, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Q1 - Conversation Length
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.05, w: 9.2, h: 1.35,
    fill: { color: C.card }, line: { color: C.yellow, width: 1.2 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.05, w: 0.07, h: 1.35, fill: { color: C.yellow }, line: { color: C.yellow } });
  // Chat bubbles visual
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.0, y: 1.12, w: 1.3, h: 0.38, fill: { color: C.yellow, transparency: 30 }, line: { color: C.yellow }, rectRadius: 0.1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.7, y: 1.58, w: 1.6, h: 0.38, fill: { color: C.accent, transparency: 30 }, line: { color: C.accent }, rectRadius: 0.1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.1, y: 2.04, w: 1.2, h: 0.28, fill: { color: C.yellow, transparency: 30 }, line: { color: C.yellow }, rectRadius: 0.1 });
  s.addText("Q1", { x: 0.5, y: 1.1, w: 0.5, h: 0.3, fontSize: 11, bold: true, color: C.yellow, fontFace: "Calibri", margin: 0 });
  s.addText("How long are conversations? Do they vary by researcher type?", {
    x: 0.65, y: 1.1, w: 7.1, h: 0.42,
    fontSize: 16, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Are RSE conversations longer and more iterative than student conversations? Do certain research domains produce deeper sessions? Understanding session depth helps us tailor onboarding and training by role.", {
    x: 0.65, y: 1.55, w: 7.1, h: 0.72,
    fontSize: 10.5, color: C.offwhite, fontFace: "Calibri", margin: 0
  });

  // Q2 - Prompt vs Code
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 2.52, w: 9.2, h: 1.35,
    fill: { color: C.card }, line: { color: C.purple, width: 1.2 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.52, w: 0.07, h: 1.35, fill: { color: C.purple }, line: { color: C.purple } });
  // Token visual
  s.addShape(pres.shapes.RECTANGLE, { x: 7.9, y: 2.6, w: 1.5, h: 0.28, fill: { color: C.purple, transparency: 20 }, line: { color: C.purple } });
  s.addText("10,000 in", { x: 7.9, y: 2.6, w: 1.5, h: 0.28, fontSize: 9, bold: true, color: C.white, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 8.4, y: 3.0, w: 0.9, h: 0.22, fill: { color: C.accent, transparency: 20 }, line: { color: C.accent } });
  s.addText("50 out", { x: 8.4, y: 3.0, w: 0.9, h: 0.22, fontSize: 9, bold: true, color: C.white, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });
  s.addText("Q2", { x: 0.5, y: 2.57, w: 0.5, h: 0.3, fontSize: 11, bold: true, color: C.purple, fontFace: "Calibri", margin: 0 });
  s.addText("Prompt vs Code Ratio -- Is the interaction efficient?", {
    x: 0.65, y: 2.57, w: 7.1, h: 0.42,
    fontSize: 16, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("If 10,000 tokens go in as context and prompting, but only 50 tokens of real code come out -- is that efficient? What is the ratio of useful output to input effort, and how does it vary by task type?", {
    x: 0.65, y: 3.02, w: 7.1, h: 0.72,
    fontSize: 10.5, color: C.offwhite, fontFace: "Calibri", margin: 0
  });

  // Q3 - RSE Plugin skills
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.0, w: 9.2, h: 1.08,
    fill: { color: C.card }, line: { color: C.pink, width: 1.2 }, shadow: makeShadow()
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.0, w: 0.07, h: 1.08, fill: { color: C.pink }, line: { color: C.pink } });
  s.addText("Q3", { x: 0.5, y: 4.05, w: 0.5, h: 0.28, fontSize: 11, bold: true, color: C.pink, fontFace: "Calibri", margin: 0 });
  s.addText("Which RSE-Plugin skills get triggered most? How much rework follows?", {
    x: 0.65, y: 4.05, w: 8.4, h: 0.38,
    fontSize: 16, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Track /research, /plan, /implement, /validate usage frequency and follow-up iteration rate as a quasi-evaluation of skill effectiveness in a given research context.", {
    x: 0.65, y: 4.45, w: 8.4, h: 0.55,
    fontSize: 10.5, color: C.offwhite, fontFace: "Calibri", margin: 0
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 6: Research Survey ───────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }, line: { color: C.accent } });

  s.addText("Researcher Survey", {
    x: 0.5, y: 0.15, w: 9, h: 0.5,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Before building more features -- understand what researchers actually want answered", {
    x: 0.5, y: 0.62, w: 9, h: 0.28,
    fontSize: 12, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Left col - survey sections
  const sections = [
    { label: "About You", items: ["Role (RSE, grad student, faculty...)", "Experience with AI coding tools", "Frequency of use"], color: C.accent },
    { label: "How You Use It", items: ["Main use cases (debugging, writing, docs...)", "Typical conversation style (1-turn vs iterative)", "How often you rework the output"], color: C.yellow },
    { label: "Prompting", items: ["Confidence in writing prompts", "Have you asked the same thing 5 different ways?", "What would help you prompt better?"], color: C.purple },
    { label: "What Would Help", items: ["Rank: guides, workshops, community, plugins...", "Where AI gets it wrong for your work", "One thing you wish AI could do better"], color: C.pink },
  ];

  sections.forEach((sec, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.4 + col * 4.7;
    const y = 1.05 + row * 1.6;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: 4.4, h: 1.42,
      fill: { color: C.card }, line: { color: sec.color, width: 1 }
    });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.4, h: 0.06, fill: { color: sec.color }, line: { color: sec.color } });
    s.addText(sec.label, {
      x: x + 0.12, y: y + 0.1, w: 4.16, h: 0.28,
      fontSize: 12, bold: true, color: C.white, fontFace: "Calibri", margin: 0
    });
    s.addText(sec.items.map((it, j) => ({
      text: it,
      options: { bullet: true, breakLine: j < sec.items.length - 1, fontSize: 9.5, color: C.offwhite }
    })), { x: x + 0.12, y: y + 0.42, w: 4.1, h: 0.9, margin: 0 });
  });

  // Survey link
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.32, w: 9.2, h: 0.58,
    fill: { color: "12172A" }, line: { color: C.accent, width: 1.5 }
  });
  s.addText("Full survey: github.com/bhagyashreewagh/llmaven-azure-demo/blob/main/research_survey.md", {
    x: 0.5, y: 4.32, w: 9, h: 0.58,
    fontSize: 12, color: C.accent, fontFace: "Calibri",
    align: "center", valign: "middle", margin: 0,
    hyperlink: { url: "https://github.com/bhagyashreewagh/llmaven-azure-demo/blob/main/research_survey.md" }
  });

  s.addText("5 minutes to complete  |  No right or wrong answers  |  Fully anonymous", {
    x: 0.5, y: 5.0, w: 9, h: 0.3,
    fontSize: 10, color: C.muted, fontFace: "Calibri", align: "center", margin: 0
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 7: Teaching AI Use ───────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.pink }, line: { color: C.pink } });

  s.addText("The Bigger Goal", {
    x: 0.5, y: 0.15, w: 9, h: 0.5,
    fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });

  // Big quote
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 0.85, w: 9, h: 1.5,
    fill: { color: C.card }, line: { color: C.pink, width: 1 }
  });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.85, w: 0.08, h: 1.5, fill: { color: C.pink }, line: { color: C.pink } });
  s.addText("The way we teach researchers GitHub and CI/CD -- we want to teach effective AI use.", {
    x: 0.75, y: 0.95, w: 8.5, h: 0.75,
    fontSize: 19, italic: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("How do we partner with researchers to show how to use AI coding assistants correctly and effectively?", {
    x: 0.75, y: 1.7, w: 8.5, h: 0.55,
    fontSize: 12, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Three pillars
  const pillars = [
    { title: "Learn from the Data", body: "Use LLMaven logs to understand usage patterns, session depth, model preferences, and where researchers struggle.", color: C.accent },
    { title: "Build Better Tools", body: "RSE-Plugins, custom skills, and domain-specific agents that help researchers work more effectively with AI.", color: C.yellow },
    { title: "Teach and Scale", body: "Train researchers how to prompt effectively, just as we teach version control, testing, and reproducibility.", color: C.purple },
  ];

  const pw = 2.85;
  pillars.forEach((p, i) => {
    const x = 0.4 + i * (pw + 0.22);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.6, w: pw, h: 2.5,
      fill: { color: C.card }, line: { color: p.color, width: 1.2 }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 2.6, w: pw, h: 0.07, fill: { color: p.color }, line: { color: p.color } });
    // Number circle
    s.addShape(pres.shapes.OVAL, { x: x + pw/2 - 0.3, y: 2.72, w: 0.6, h: 0.6, fill: { color: p.color, transparency: 20 }, line: { color: p.color } });
    s.addText(String(i + 1), {
      x: x + pw/2 - 0.3, y: 2.72, w: 0.6, h: 0.6,
      fontSize: 18, bold: true, color: C.white, fontFace: "Calibri",
      align: "center", valign: "middle", margin: 0
    });
    s.addText(p.title, {
      x: x + 0.12, y: 3.45, w: pw - 0.24, h: 0.4,
      fontSize: 13, bold: true, color: C.white, fontFace: "Calibri",
      align: "center", margin: 0
    });
    s.addText(p.body, {
      x: x + 0.15, y: 3.9, w: pw - 0.3, h: 1.1,
      fontSize: 10, color: C.offwhite, fontFace: "Calibri", margin: 0
    });
  });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Slide 8: Updated Architecture (Callback Push) ─────────────────────────────
{
  const s = pres.addSlide();
  s.background = { color: C.bg };

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }, line: { color: C.accent } });

  s.addText("Potential Next Step: Push-Based Architecture", {
    x: 0.5, y: 0.15, w: 9, h: 0.5,
    fontSize: 22, bold: true, color: C.white, fontFace: "Calibri", margin: 0
  });
  s.addText("Replace scheduled pull with a real-time LiteLLM callback -- data arrives within seconds, not 24 hours later", {
    x: 0.5, y: 0.62, w: 9, h: 0.28,
    fontSize: 11, color: C.muted, fontFace: "Calibri", margin: 0
  });

  // Current vs Updated side by side
  // Current
  s.addShape(pres.shapes.RECTANGLE, { x: 0.3, y: 1.0, w: 4.2, h: 0.38, fill: { color: C.border }, line: { color: C.border } });
  s.addText("CURRENT (Pull)", { x: 0.3, y: 1.0, w: 4.2, h: 0.38, fontSize: 12, bold: true, color: C.muted, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  const currentSteps = ["LLMaven logs to PostgreSQL", "Azure Function wakes up nightly", "Pulls yesterdays data via extract", "Uploads to Data Lake"];
  currentSteps.forEach((step, i) => {
    const y = 1.5 + i * 0.72;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.4, y, w: 4.0, h: 0.55,
      fill: { color: C.card }, line: { color: C.border, width: 1 }
    });
    s.addText(step, { x: 0.55, y, w: 3.7, h: 0.55, fontSize: 11, color: C.offwhite, fontFace: "Calibri", valign: "middle", margin: 0 });
    if (i < currentSteps.length - 1) {
      s.addShape(pres.shapes.RECTANGLE, { x: 2.3, y: y + 0.55, w: 0.04, h: 0.17, fill: { color: C.border }, line: { color: C.border } });
    }
  });

  // Badge: up to 24hr delay
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.5, w: 3.8, h: 0.38, fill: { color: "3D1515" }, line: { color: "FF6B6B", width: 1 } });
  s.addText("Up to 24 hour data delay", { x: 0.5, y: 4.5, w: 3.8, h: 0.38, fontSize: 11, color: "FF6B6B", fontFace: "Calibri", align: "center", valign: "middle", bold: true, margin: 0 });

  // Updated
  s.addShape(pres.shapes.RECTANGLE, { x: 5.5, y: 1.0, w: 4.2, h: 0.38, fill: { color: C.accent, transparency: 80 }, line: { color: C.accent } });
  s.addText("UPDATED (Push Callback)", { x: 5.5, y: 1.0, w: 4.2, h: 0.38, fontSize: 12, bold: true, color: C.accent, fontFace: "Calibri", align: "center", valign: "middle", margin: 0 });

  const updatedSteps = [
    { text: "User request processed by LiteLLM", color: C.border },
    { text: "LiteLLM fires Python callback instantly", color: C.accent },
    { text: "Callback pushes JSON to Azure endpoint", color: C.accent },
    { text: "Data in lake within seconds", color: C.accent },
  ];
  updatedSteps.forEach((step, i) => {
    const y = 1.5 + i * 0.72;
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.6, y, w: 4.0, h: 0.55,
      fill: { color: C.card }, line: { color: step.color, width: i === 0 ? 1 : 1.5 }
    });
    s.addText(step.text, { x: 5.75, y, w: 3.7, h: 0.55, fontSize: 11, color: i === 0 ? C.offwhite : C.white, fontFace: "Calibri", bold: i > 0, valign: "middle", margin: 0 });
    if (i < updatedSteps.length - 1) {
      s.addShape(pres.shapes.RECTANGLE, { x: 7.55, y: y + 0.55, w: 0.04, h: 0.17, fill: { color: C.accent }, line: { color: C.accent } });
    }
  });

  // Badge: real time
  s.addShape(pres.shapes.RECTANGLE, { x: 5.7, y: 4.5, w: 3.8, h: 0.38, fill: { color: "0D2B22" }, line: { color: C.accent, width: 1 } });
  s.addText("Real-time -- seconds not hours", { x: 5.7, y: 4.5, w: 3.8, h: 0.38, fontSize: 11, color: C.accent, fontFace: "Calibri", align: "center", valign: "middle", bold: true, margin: 0 });

  // Advantages
  const advs = ["No scheduled jobs to maintain", "Always up to date -- no 24hr lag", "One less moving part (no Azure Function)", "Requires LLMaven admin to point callback at our Azure endpoint"];
  s.addText(advs.map((a, i) => ({
    text: a,
    options: { bullet: true, breakLine: i < advs.length - 1, fontSize: 9.5, color: C.muted }
  })), { x: 0.5, y: 5.0, w: 9, h: 0.45, margin: 0 });

  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.525, w: 10, h: 0.1, fill: { color: C.border }, line: { color: C.border } });
}

// ── Write file ─────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: path.join(__dirname, "LLMaven_Pipeline_Presentation.pptx") })
  .then(() => console.log("Done: LLMaven_Pipeline_Presentation.pptx"))
  .catch(err => console.error("Error:", err));
