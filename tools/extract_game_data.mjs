// One-off helper: lifts the game data tables out of the legacy Next.js sources into static JSON.
//   node tools/extract_game_data.mjs /path/to/ryu_new/frontend/src
// Output: static/data/games.json and static/data/speed_quiz.json  (commit the JSON, not this input path)
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const src = process.argv[2];
if (!src) { console.error('usage: node extract_game_data.mjs <ryu_new/frontend/src>'); process.exit(1); }
const out = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../static/data');
const games = fs.readFileSync(path.join(src, 'app/games/page.tsx'), 'utf8').split('\n');

const strip = (s) => s.replace(/:\s*(MenuItem|CounterItem|GameMeta)\[\]/g, '');
const evalArray = (code, name) => vm.runInNewContext(`${strip(code)}; ${name}`);
const slice = (a, b) => games.slice(a - 1, b).join('\n');   // 1-based inclusive line numbers

const top = slice(68, 259) + '\n';
const data = vm.runInNewContext(`${strip(top)}; ({ALL_MENU_ITEMS, COUNTER_ITEMS_10, CUSTOMER_EMOJIS, CUSTOMER_NAMES, GAMES_LIST, SENTENCE_POOL})`);
data.KANA_POOL = evalArray(slice(344, 380).replace('const pool =', 'var pool ='), 'pool');
data.MEMORY_PAIRS = evalArray(slice(631, 638).replace('const vocabPairs =', 'var vocabPairs ='), 'vocabPairs');
data.BOSS_POOL = evalArray(slice(691, 704).replace('const bossVocabPool =', 'var bossVocabPool ='), 'bossVocabPool');
data.SURVIVAL_POOL = evalArray(slice(760, 781).replace('const survivalPool =', 'var survivalPool ='), 'survivalPool');
fs.writeFileSync(path.join(out, 'games.json'), JSON.stringify(data));

let sq = fs.readFileSync(path.join(src, 'lib/speedQuizData.ts'), 'utf8');
sq = sq.slice(sq.indexOf('export const SPEED_QUIZ_QUESTIONS'), sq.indexOf('export function getQuestionsByLevel'))
  .replace('export const SPEED_QUIZ_QUESTIONS: QuizQuestion[] =', 'var Q =');
fs.writeFileSync(path.join(out, 'speed_quiz.json'), JSON.stringify(vm.runInNewContext(`${sq}; Q`)));
console.log(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v.length])));
