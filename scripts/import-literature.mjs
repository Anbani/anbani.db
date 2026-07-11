import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'

const ROOT = new URL('../datasets/literature/', import.meta.url)
const API = 'https://ka.wikisource.org/w/api.php'

const sources = [
  ['sibrdze-sitsruisa', 'წიგნი სიბრძნე სიცრუისა', 76066, 0],
  ['kacia-adamiani', 'კაცია-ადამიანი?!', 73882, 1],
  ['otaraanth-qvrivi', 'ოთარაანთ ქვრივი', 74859, 2],
  ['khevisberi-gocha', 'ხევის ბერი გოჩა', 76132, 3],
  ['shvlis-nukris-naambobi', 'შვლის ნუკრის ნაამბობი', 77352, 4],
  ['samanishvilis-dedinacvali', 'სამანიშვილის დედინაცვალი', 75105, 5],
  ['jaqos-khiznebi', 'ჯაყოს ხიზნები', 76208, 6],
  ['gogia-uishvili', 'გოგია უიშვილი', 73009, 7],
  ['merani', 'მერანი', 74366, 9],
  ['stumarmaspindzeli', 'სტუმარ-მასპინძელი', 75306, 10],
  ['aluda-qetelauri', 'ალუდა ქეთელაური', 72525, 11],
  ['gandegili', 'განდეგილი', 72897, 12],
  ['gamzrdeli', 'გამზრდელი', 72887, 13],
  ['tano-tatano', 'ტანო ტატანო', 75343, 15],
  ['leqsi-myeqeri', 'ლექსი მეწყერი', 77801, 16],
  ['memento-mori', 'MEMENTO MORI', 72209, 17],
]

const entities = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' }
function decode(value) {
  return value
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([\da-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/&([a-z]+);/gi, (match, name) => entities[name] ?? match)
}

// MediaWiki's parse output resolves transclusions but contains presentation HTML.
// Keep literary line breaks and headings while removing templates and apparatus.
function plainText(html) {
  return decode(html)
    .replace(/<table\b[\s\S]*?<\/table>/gi, '')
    .replace(/<ul\b[\s\S]*?<\/ul>/gi, '')
    .replace(/<(ol|div)\b[^>]*class="[^"]*(references|mw-references-wrap)[^"]*"[^>]*>[\s\S]*?<\/\1>/gi, '')
    .replace(/<(style|script|sup)\b[\s\S]*?<\/\1>/gi, '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/(p|div|h[1-6]|li|blockquote)>/gi, '\n\n')
    .replace(/<li\b[^>]*>/gi, '• ')
    .replace(/<[^>]+>/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n[ \t]+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\nრესურსები ინტერნეტში[\s\S]*$/g, '')
    .trim()
    .normalize('NFC') + '\n'
}

for (const [id, page, revision, cacheIndex] of sources) {
  const params = new URLSearchParams({
    action: 'parse', oldid: String(revision), prop: 'text|revid',
    format: 'json', formatversion: '2',
  })
  let data
  if (process.env.ANBANI_WIKISOURCE_CACHE) {
    data = JSON.parse(await readFile(`${process.env.ANBANI_WIKISOURCE_CACHE}/anbani-ws-${cacheIndex}.json`, 'utf8'))
  } else {
    const response = await fetch(`${API}?${params}`, {
      headers: { 'user-agent': 'AnbaniLibraryBot/1.0 (https://anbani.ge)' },
    })
    if (!response.ok) throw new Error(`${page}: HTTP ${response.status}`)
    data = await response.json()
  }
  if (data.parse.revid !== revision) throw new Error(`${page}: revision mismatch`)
  const text = plainText(data.parse.text)
  const directory = new URL(`./${id}/`, ROOT)
  await mkdir(directory, { recursive: true })
  await writeFile(new URL('text.txt', directory), text)
  await writeFile(new URL('source.json', directory), JSON.stringify({
    source: 'Georgian Wikisource',
    page,
    url: `https://ka.wikisource.org/wiki/${encodeURIComponent(page.replaceAll(' ', '_'))}?oldid=${revision}`,
    revision,
    retrieved: new Date().toISOString().slice(0, 10),
    transcription_license: 'CC BY-SA 4.0',
    sha256: createHash('sha256').update(text).digest('hex'),
  }, null, 2) + '\n')
  console.log(`${id}: ${text.length.toLocaleString()} characters`)
}
