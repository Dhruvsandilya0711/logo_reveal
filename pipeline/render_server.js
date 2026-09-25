// Headless frame renderer: loads reel<res>.html#reel once, then renders every job
// in a JSON-lines file:  {"kind":"trick"|"relief", "out":"path.png", ...params}
// usage: node render_server.js jobs.jsonl [res]
const fs = require("fs");
const path = require("path");
const { chromium } = require(process.env.PW_MODULE || "/opt/node22/lib/node_modules/playwright");

(async () => {
  const jobsFile = process.argv[2];
  const res = process.argv[3] || "1024";
  const jobs = fs.readFileSync(jobsFile, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  const browser = await chromium.launch({
    executablePath: "/opt/pw-browsers/chromium",
    args: ["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
  });
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  page.on("console", (m) => { if (m.type() === "warning" || m.type() === "error") console.error("[page]", m.text()); });
  await page.goto("file://" + path.resolve(__dirname, `reel${res}.html`) + "#reel");
  await page.waitForFunction(() => window.__done === true, null, { timeout: 120000 });
  let n = 0;
  const t0 = Date.now();
  for (const job of jobs) {
    if (!process.env.FORCE && fs.existsSync(job.out)) { n++; continue; }
    const url = await page.evaluate(([k, o]) => {
      const u = window.__r3(k, o);
      return { u, floor: window.__floor || null };
    }, [job.kind, job]);
    fs.mkdirSync(path.dirname(job.out), { recursive: true });
    fs.writeFileSync(job.out, Buffer.from(url.u.split(",")[1], "base64"));
    if (url.floor) fs.writeFileSync(job.out.replace(/\.png$/, ".json"), JSON.stringify({ floor: url.floor }));
    n++;
    if (n % 10 === 0) console.log(`${n}/${jobs.length}  ${((Date.now() - t0) / n / 1000).toFixed(2)} s/frame`);
  }
  console.log(`done ${n} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  await browser.close();
})();
