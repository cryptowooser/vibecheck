import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'

const ROOT = process.cwd()
const SCAN_DIRS = ['src', 'dist']
const IGNORED_PATH_SNIPPETS = [
  `${path.sep}node_modules${path.sep}`,
  `${path.sep}e2e${path.sep}`,
  `${path.sep}test-results${path.sep}`,
  `${path.sep}playwright-report${path.sep}`,
]
const IGNORED_FILE_SUFFIXES = ['.test.js', '.test.ts', '.spec.js', '.spec.ts']
const SECRET_PATTERNS = [
  { name: 'MISTRAL_API_KEY', regex: /MISTRAL_API_KEY/g },
  { name: 'ELEVENLABS_API_KEY', regex: /ELEVENLABS_API_KEY/g },
  { name: 'api.mistral.ai', regex: /api\.mistral\.ai/g },
  { name: 'api.elevenlabs.io', regex: /api\.elevenlabs\.io/g },
  { name: 'xi-api-key', regex: /xi-api-key/g },
]

function shouldSkipFile(filePath) {
  if (IGNORED_FILE_SUFFIXES.some((suffix) => filePath.endsWith(suffix))) {
    return true
  }
  return IGNORED_PATH_SNIPPETS.some((snippet) => filePath.includes(snippet))
}

async function* walkFiles(dirPath) {
  let entries = []
  try {
    entries = await readdir(dirPath, { withFileTypes: true })
  } catch {
    return
  }

  for (const entry of entries) {
    const entryPath = path.join(dirPath, entry.name)
    if (entry.isDirectory()) {
      yield* walkFiles(entryPath)
      continue
    }
    yield entryPath
  }
}

const findings = []

for (const scanDir of SCAN_DIRS) {
  const absoluteDir = path.join(ROOT, scanDir)
  for await (const filePath of walkFiles(absoluteDir)) {
    if (shouldSkipFile(filePath)) {
      continue
    }

    let content = ''
    try {
      content = await readFile(filePath, 'utf8')
    } catch {
      continue
    }

    for (const { name, regex } of SECRET_PATTERNS) {
      if (regex.test(content)) {
        findings.push({ filePath, name })
      }
      regex.lastIndex = 0
    }
  }
}

if (findings.length > 0) {
  console.error('Potential secret/provider leakage patterns found:')
  for (const finding of findings) {
    const relativePath = path.relative(ROOT, finding.filePath)
    console.error(`- ${relativePath}: ${finding.name}`)
  }
  process.exit(1)
}

console.log('Secret scan passed: no forbidden key/provider patterns found in src or dist.')
