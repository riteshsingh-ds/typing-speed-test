// Tests the real frontend/typing_engine/index.html inside jsdom with real timers.
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const HTML = fs.readFileSync(path.join(__dirname, "../../frontend/typing_engine/index.html"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function boot() {
  const dom = new JSDOM(HTML, { runScripts: "dangerously", pretendToBeVisual: true });
  const w = dom.window;
  const out = [];
  w.addEventListener("message", (e) => { if (e.data && e.data.isStreamlitMessage) out.push(e.data); });
  const $ = (id) => w.document.getElementById(id);
  return {
    w, out, $,
    render: async (args) => { w.postMessage({ type: "streamlit:render", args }, "*"); await sleep(20); },
    type: (value) => { const i = $("input"); i.value = value; i.dispatchEvent(new w.Event("input", { bubbles: true })); },
    results: () => out.filter((m) => m.type === "streamlit:setComponentValue"),
    cls: (i) => $("text").children[i].className,
    close: () => w.close(),
  };
}

const tests = [];
const test = (name, fn) => tests.push([name, fn]);

test("announces readiness with apiVersion 1", async () => {
  const t = boot(); await sleep(20);
  const ready = t.out.find((m) => m.type === "streamlit:componentReady");
  assert(ready && ready.apiVersion === 1); t.close();
});

test("renders one span per character and idle stats", async () => {
  const t = boot();
  await t.render({ test_id: "a", text: "hello world", duration: 30, personal_best: 55 });
  assert.strictEqual(t.$("text").children.length, 11);
  assert.strictEqual(t.$("time").textContent, "30s");
  assert.strictEqual(t.$("wpm").textContent, "0");
  assert.strictEqual(t.$("pb").textContent, "55");
  assert(t.cls(0).includes("cur"));
  assert(!t.$("app").classList.contains("loading")); t.close();
});

test("green for correct, red for wrong, live counters", async () => {
  const t = boot();
  await t.render({ test_id: "a", text: "hello world", duration: 30, personal_best: null });
  t.type("hexlo");
  assert(t.cls(0).includes("ok") && t.cls(1).includes("ok"));
  assert(t.cls(2).includes("bad"));
  assert(t.cls(3).includes("ok") && t.cls(4).includes("ok"));
  assert(t.cls(5).includes("cur"));
  assert.strictEqual(t.$("cor").textContent, "4");
  assert.strictEqual(t.$("mis").textContent, "1");
  assert.strictEqual(t.$("acc").textContent, "80.0%");
  assert.strictEqual(t.$("pb").textContent, "--");
  t.type("hex");                                   // backspace corrects state
  assert.strictEqual(t.$("mis").textContent, "1");
  t.type("he");
  assert.strictEqual(t.$("mis").textContent, "0");
  assert.strictEqual(t.$("acc").textContent, "100.0%");
  t.close();
});

test("reports positions that were ever typed wrong, even after correction", async () => {
  const t = boot();
  await t.render({ test_id: "w1", text: "abcdefg", duration: 30 });
  t.type("abX"); t.type("ab"); t.type("abcdeZ"); t.type("abcde"); t.type("abcdefg"); await sleep(40);
  const v = t.results()[0].value;
  assert.deepStrictEqual(Array.from(v.ever_wrong), [2, 5]);
  assert.strictEqual(v.typed, "abcdefg"); t.close();
});

test("timer starts on first keystroke only", async () => {
  const t = boot();
  await t.render({ test_id: "a", text: "hello world", duration: 30 });
  await sleep(350);
  assert.strictEqual(t.$("time").textContent, "30s");
  assert(t.$("stage").className.includes("ready"));
  t.type("h");
  assert(t.$("stage").className.includes("running")); t.close();
});

test("rerenders with the same test id never reset a running test", async () => {
  const t = boot();
  await t.render({ test_id: "a", text: "hello world", duration: 30 });
  t.type("hel");
  for (let i = 0; i < 5; i++) await t.render({ test_id: "a", text: "hello world", duration: 30, personal_best: 99 });
  assert.strictEqual(t.$("cor").textContent, "3");
  assert(t.$("stage").className.includes("running"));
  assert.strictEqual(t.results().length, 0);
  await t.render({ test_id: "b", text: "other text", duration: 30 });   // a NEW test does reset
  assert.strictEqual(t.$("cor").textContent, "0");
  assert.strictEqual(t.$("text").children.length, 10); t.close();
});

test("timer ends the test and posts exactly one result", async () => {
  const t = boot();
  await t.render({ test_id: "tm", text: "abcdefghijklmnopqrstuvwxyz", duration: 2, personal_best: null });
  t.type("abcdexgh");
  await sleep(2500);
  const r = t.results();
  assert.strictEqual(r.length, 1, "exactly one setComponentValue");
  const v = r[0].value;
  assert.strictEqual(r[0].dataType, "json");
  assert.strictEqual(v.test_id, "tm");
  assert.strictEqual(v.typed, "abcdexgh");
  assert.strictEqual(v.reason, "time");
  assert(v.elapsed_ms >= 1990 && v.elapsed_ms <= 2000, "clamped to duration, got " + v.elapsed_ms);
  assert.strictEqual(v.series.length, 2);
  assert.strictEqual(v.client.accuracy, 87.5);                 // 7 of 8 correct
  assert.strictEqual(v.client.wpm, Math.round(7 / 5 / (2 / 60) * 10) / 10);
  assert(t.$("input").disabled);
  assert(t.$("stage").className.includes("done"));
  assert.strictEqual(t.$("time").textContent, "0s");
  t.type("abcdexghi");                                          // typing after the buzzer is ignored
  await sleep(300);
  assert.strictEqual(t.results().length, 1); t.close();
});

test("finishing the passage early ends the test", async () => {
  const t = boot();
  await t.render({ test_id: "e", text: "abc def", duration: 30 });
  t.type("a"); await sleep(1200); t.type("abc def"); await sleep(40);   // postMessage is async
  const r = t.results();
  assert.strictEqual(r.length, 1);
  assert.strictEqual(r[0].value.reason, "completed");
  assert(r[0].value.elapsed_ms >= 1100 && r[0].value.elapsed_ms < 2500);
  t.close();
});

test("input is clamped to passage length and newlines are stripped", async () => {
  const t = boot();
  await t.render({ test_id: "c", text: "abc", duration: 30 });
  t.type("ab\ncXYZ"); await sleep(40);
  assert.strictEqual(t.results().length, 1);
  assert.strictEqual(t.results()[0].value.typed, "abc"); t.close();
});

test("paste, cut and drop are blocked", async () => {
  const t = boot();
  await t.render({ test_id: "p", text: "abc", duration: 30 });
  for (const name of ["paste", "cut", "drop"]) {
    const ev = new t.w.Event(name, { bubbles: true, cancelable: true });
    t.$("input").dispatchEvent(ev);
    assert.strictEqual(ev.defaultPrevented, true, name + " should be prevented");
  }
  t.close();
});

test("Enter and caret-moving keys are blocked", async () => {
  const t = boot();
  await t.render({ test_id: "k", text: "abc", duration: 30 });
  for (const key of ["Enter", "ArrowLeft", "Home"]) {
    const ev = new t.w.KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
    t.$("input").dispatchEvent(ev);
    assert.strictEqual(ev.defaultPrevented, true, key);
  }
  const ok = new t.w.KeyboardEvent("keydown", { key: "a", bubbles: true, cancelable: true });
  t.$("input").dispatchEvent(ok);
  assert.strictEqual(ok.defaultPrevented, false); t.close();
});

test("warning style appears in the last 5 seconds", async () => {
  const t = boot();
  await t.render({ test_id: "w", text: "abcdefghij", duration: 6 });
  t.type("a");
  await sleep(1300);
  assert(t.$("timeCard").classList.contains("warn")); t.close();
});

(async () => {
  let failed = 0;
  for (const [name, fn] of tests) {
    try { await fn(); console.log("  ok   " + name); }
    catch (e) { failed++; console.log("  FAIL " + name + "\n       " + e.message); }
  }
  console.log(`\n${tests.length - failed}/${tests.length} passed`);
  process.exit(failed ? 1 : 0);
})();
