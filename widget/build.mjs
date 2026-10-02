import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { transform } from "esbuild";

const css = readFileSync("src/chatbot.css", "utf8");
const js = readFileSync("src/chatbot.js", "utf8");

// Minificar CSS
const cssMin = (
  await transform(css, {
    loader: "css",
    minify: true
  })
).code;

// Inyectar CSS en JS
const jsConCss = js.replace(
  '"__CHATBOT_CSS__"',
  () => JSON.stringify(cssMin)
);

// Minificar JS
const out = await transform(jsConCss, {
  minify: true
});

mkdirSync("build", { recursive: true });

writeFileSync(
  "build/chatbot.min.js",
  out.code
);

console.log("Generado build/chatbot.min.js");