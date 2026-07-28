import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import ts from 'typescript'

const ROOT = process.cwd()
const SCAN_ROOTS = [
  'src/App.tsx',
  'src/components',
  'src/contexts',
  'src/pages',
  'src/plugins'
]

const USER_FACING_ATTRIBUTES = new Set([
  'alt',
  'aria-label',
  'cancelLabel',
  'confirmLabel',
  'description',
  'emptyText',
  'helpText',
  'label',
  'message',
  'placeholder',
  'title',
  'tooltip'
])

const USER_FACING_OBJECT_KEYS = new Set([
  'cancelLabel',
  'confirmLabel',
  'description',
  'emptyText',
  'helpText',
  'label',
  'message',
  'placeholder',
  'title',
  'tooltip'
])

const USER_FACING_CALLS = /(?:^|\.)(?:alert|confirm|setBanner|setErrorMsg|showToast|toast|writeLine)$/

// Product names, protocols, file names, commands, paths, config keys, and
// example values are intentionally shown verbatim in every locale.
const ALLOWED_EXACT = new Set([
  '$HERMES_HOME/backups/hermes-backup.zip',
  '-y @modelcontextprotocol/server',
  '-y @modelcontextprotocol/server-foo',
  '.log',
  '/absolute/project/path',
  '/usr/local/bin/my-hook.sh',
  'Agent',
  'API_KEY=secret DEBUG=1',
  'CPU',
  'Discord',
  'EN',
  'HTTP',
  'HTTP/SSE',
  'Hermes',
  'MCP',
  'MEMORY.md',
  'Nous Portal',
  'OAuth',
  'Python',
  'SKILL.md',
  'Slack',
  'Telegram',
  'URL',
  'USER.md',
  'YAML',
  'compressor',
  'dashboard.show_token_analytics',
  'dashboard.show_token_analytics: true',
  'devops',
  'hermes skills search',
  'https://api.example.com/v1',
  'https://example.com/mcp',
  'my-server',
  'my-skill',
  'npx',
  'openrouter',
  'relative/path/in/scripts',
  'sk-\u2026',
  'stdio',
  '~/.hermes/.env'
])

const ALLOWED_PATTERNS = [
  /^\s*[\u2014\u00b7]\s*(?:MEMORY|USER)\.md:\s*$/,
  /^(?:https?:\/\/|git@)/,
  /^(?:\$?[A-Z][A-Z0-9_]*=\S+)(?:\s+[A-Z][A-Z0-9_]*=\S+)*$/,
  /^[-\w./~@$:{}]+\.(?:json|log|md|toml|ya?ml|zip)(?::\s*)?$/i,
  /^hermes(?:\s|$)/,
  /^dashboard\.[a-z0-9_.:-]+(?:\s*:\s*(?:true|false))?$/i
]

function collectTsxFiles(entry, files) {
  const absolute = path.resolve(ROOT, entry)
  const stat = fs.statSync(absolute)
  if (stat.isFile()) {
    if (absolute.endsWith('.tsx')) files.push(absolute)
    return
  }
  for (const child of fs.readdirSync(absolute, { withFileTypes: true })) {
    collectTsxFiles(path.join(absolute, child.name), files)
  }
}

function normalize(value) {
  return value.replace(/\s+/g, ' ').trim()
}

function hasEnglishWords(value) {
  return /[A-Za-z]{2}/.test(value)
}

function isAllowed(value) {
  const trimmed = value.replace(/^\s*[\u2014\u00b7]\s*/, '').replace(/:\s*$/, '')
  return (
    ALLOWED_EXACT.has(value) ||
    ALLOWED_EXACT.has(trimmed) ||
    ALLOWED_PATTERNS.some((pattern) => pattern.test(value))
  )
}

function expressionUsesTranslation(node, sourceFile) {
  const source = node.getText(sourceFile)
  return /(?:^|[^\w])(?:t|L)\./.test(source) || source.includes('formatMessage(')
}

function literalValue(node) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
    return node.text
  }
  if (ts.isTemplateExpression(node)) {
    return [node.head.text, ...node.templateSpans.map((span) => span.literal.text)].join(' ')
  }
  return null
}

function propertyName(node) {
  if (!node.name) return null
  if (ts.isIdentifier(node.name) || ts.isStringLiteral(node.name)) return node.name.text
  return null
}

const files = []
for (const root of SCAN_ROOTS) collectTsxFiles(root, files)

const findings = []
const reported = new Set()

for (const file of files.sort()) {
  const sourceFile = ts.createSourceFile(
    file,
    fs.readFileSync(file, 'utf8'),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX
  )

  const report = (node, kind, rawValue) => {
    const value = normalize(rawValue)
    if (!value || !hasEnglishWords(value) || isAllowed(value)) return
    const position = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile))
    const key = `${file}:${position.line}:${kind}:${value}`
    if (reported.has(key)) return
    reported.add(key)
    findings.push({
      file: path.relative(ROOT, file),
      line: position.line + 1,
      column: position.character + 1,
      kind,
      value
    })
  }

  const scanRenderedExpression = (node) => {
    if (expressionUsesTranslation(node, sourceFile)) return
    const value = literalValue(node)
    if (value !== null) {
      report(node, 'rendered text', value)
      return
    }
    if (ts.isConditionalExpression(node)) {
      scanRenderedExpression(node.whenTrue)
      scanRenderedExpression(node.whenFalse)
    } else if (ts.isParenthesizedExpression(node)) {
      scanRenderedExpression(node.expression)
    } else if (
      ts.isBinaryExpression(node) &&
      node.operatorToken.kind === ts.SyntaxKind.PlusToken
    ) {
      scanRenderedExpression(node.left)
      scanRenderedExpression(node.right)
    }
  }

  const visit = (node) => {
    if (ts.isJsxText(node)) report(node, 'JSX text', node.getText(sourceFile))

    if (ts.isJsxAttribute(node)) {
      const name = node.name.getText(sourceFile)
      if (USER_FACING_ATTRIBUTES.has(name)) {
        const initializer = node.initializer
        if (initializer && ts.isStringLiteral(initializer)) {
          report(initializer, name, initializer.text)
        } else if (initializer && ts.isJsxExpression(initializer) && initializer.expression) {
          scanRenderedExpression(initializer.expression)
        }
      }
    }

    if (ts.isJsxExpression(node) && !ts.isJsxAttribute(node.parent) && node.expression) {
      scanRenderedExpression(node.expression)
    }

    if (ts.isPropertyAssignment(node)) {
      const name = propertyName(node)
      if (name && USER_FACING_OBJECT_KEYS.has(name) && !expressionUsesTranslation(node.initializer, sourceFile)) {
        const value = literalValue(node.initializer)
        const symbolicKey = value !== null && /^[a-z][A-Za-z0-9_]*$/.test(value)
        if (value !== null && !symbolicKey) report(node.initializer, `object ${name}`, value)
      }
    }

    if (ts.isCallExpression(node)) {
      const callName = node.expression.getText(sourceFile)
      const argumentIndex = callName.endsWith('writeLine') ? 1 : 0
      if (USER_FACING_CALLS.test(callName) && node.arguments[argumentIndex]) {
        const userFacingArgument = node.arguments[argumentIndex]
        if (!expressionUsesTranslation(userFacingArgument, sourceFile)) {
          const value = literalValue(userFacingArgument)
          if (value !== null) report(userFacingArgument, callName, value)
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
}

if (findings.length) {
  console.error('Hard-coded user-facing English found in built-in Dashboard TSX:')
  for (const finding of findings) {
    console.error(
      `  ${finding.file}:${finding.line}:${finding.column} [${finding.kind}] ${finding.value}`
    )
  }
  console.error(
    '\nMove UI copy into the i18n dictionaries. Add only required names, protocols, commands, paths, or examples to the explicit allowlist.'
  )
  process.exit(1)
}

console.log(`i18n static check passed (${files.length} built-in TSX files)`)
