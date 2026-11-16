// @ts-nocheck
const vscode = require('vscode');
const { execFile, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// ============================================================
// Flow Language — Kalit so'zlar va Built-in funksiyalar
// ============================================================

const KEYWORDS = [
  { label: 'fn',     detail: 'Funksiya e\'loni',          kind: vscode.CompletionItemKind.Keyword },
  { label: 'class',  detail: 'Klass e\'loni',             kind: vscode.CompletionItemKind.Keyword },
  { label: 'var',    detail: 'O\'zgaruvchi e\'loni',      kind: vscode.CompletionItemKind.Keyword },
  { label: 'val',    detail: 'O\'zgarmas qiymat',         kind: vscode.CompletionItemKind.Keyword },
  { label: 'inner',  detail: 'Ichki funksiya',            kind: vscode.CompletionItemKind.Keyword },
  { label: 'return', detail: 'Qiymat qaytarish',          kind: vscode.CompletionItemKind.Keyword },
  { label: 'if',     detail: 'Shartli ibora',             kind: vscode.CompletionItemKind.Keyword },
  { label: 'else',   detail: 'Aks holat bloki',           kind: vscode.CompletionItemKind.Keyword },
  { label: 'for',    detail: 'for-in sikli',              kind: vscode.CompletionItemKind.Keyword },
  { label: 'while',  detail: 'while sikli',               kind: vscode.CompletionItemKind.Keyword },
  { label: 'in',     detail: 'for-in operatori',          kind: vscode.CompletionItemKind.Keyword },
  { label: 'this',   detail: 'Joriy ob\'ekt',             kind: vscode.CompletionItemKind.Keyword },
  { label: 'new',    detail: 'Ob\'ekt yaratish',          kind: vscode.CompletionItemKind.Keyword },
  { label: 'null',   detail: 'Null qiymati',              kind: vscode.CompletionItemKind.Keyword },
  { label: 'true',   detail: 'Mantiqiy rost',             kind: vscode.CompletionItemKind.Keyword },
  { label: 'false',  detail: 'Mantiqiy yolg\'on',         kind: vscode.CompletionItemKind.Keyword },
];

const TYPES = [
  { label: 'Int',     detail: 'Butun son turi',            kind: vscode.CompletionItemKind.Class },
  { label: 'Float',   detail: 'O\'nlik kasr turi',         kind: vscode.CompletionItemKind.Class },
  { label: 'Double',  detail: 'Ikki qiymatli kasr',        kind: vscode.CompletionItemKind.Class },
  { label: 'String',  detail: 'Matn turi',                 kind: vscode.CompletionItemKind.Class },
  { label: 'Boolean', detail: 'Mantiqiy tur',              kind: vscode.CompletionItemKind.Class },
  { label: 'Void',    detail: 'Qaytish qiymati yo\'q',     kind: vscode.CompletionItemKind.Class },
  { label: 'Byte',    detail: 'Bayt turi',                 kind: vscode.CompletionItemKind.Class },
  { label: 'Short',   detail: 'Qisqa butun son',           kind: vscode.CompletionItemKind.Class },
];

const BUILTINS = [
  {
    label: 'print',
    detail: 'print(value) — Konsolga chiqarish',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('print(${1:value})'),
    documentation: new vscode.MarkdownString('```flow\nprint("Salom dunyo")\n```'),
  },
  {
    label: 'len',
    detail: 'len(obj) → Int — Massiv yoki string uzunligi',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('len(${1:obj})'),
    documentation: new vscode.MarkdownString('```flow\nvar n = len("salom")  // 5\n```'),
  },
  {
    label: 'str',
    detail: 'str(obj) → String — Qiymatni String ga o\'girish',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('str(${1:obj})'),
  },
  {
    label: 'toInt',
    detail: 'toInt(obj) → Int — String/Float ni Int ga o\'girish',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('toInt(${1:obj})'),
    documentation: new vscode.MarkdownString('```flow\nvar n = toInt("42")  // 42\n```'),
  },
  {
    label: 'input',
    detail: 'input(prompt) → String — Foydalanuvchi kiritish',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('input(${1:"Kiritish: "})'),
  },
  {
    label: 'type',
    detail: 'type(obj) → String — Qiymat turini qaytarish',
    kind: vscode.CompletionItemKind.Function,
    insertText: new vscode.SnippetString('type(${1:obj})'),
    documentation: new vscode.MarkdownString('```flow\ntype(42)    // "Int"\ntype("hi")  // "String"\n```'),
  },
];

const STRING_METHODS = [
  { label: 'upper',      detail: '.upper() → String', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('upper()') },
  { label: 'lower',      detail: '.lower() → String', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('lower()') },
  { label: 'trim',       detail: '.trim() → String',  kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('trim()') },
  { label: 'length',     detail: '.length → Int',     kind: vscode.CompletionItemKind.Property, insertText: 'length' },
  { label: 'contains',   detail: '.contains(sub) → Boolean', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('contains(${1:substring})') },
  { label: 'startsWith', detail: '.startsWith(prefix) → Boolean', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('startsWith(${1:prefix})') },
  { label: 'endsWith',   detail: '.endsWith(suffix) → Boolean',   kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('endsWith(${1:suffix})') },
  { label: 'replace',    detail: '.replace(old, new) → String',   kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('replace(${1:old}, ${2:new})') },
  { label: 'split',      detail: '.split(sep) → Array',           kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('split(${1:" "})') },
];

const NUMBER_METHODS = [
  { label: 'abs',   detail: '.abs() → Number — Son moduli',             kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('abs()') },
  { label: 'round', detail: '.round() → Int — Yaxlitlash',              kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('round()') },
  { label: 'ceil',  detail: '.ceil() → Int — Yuqoriga yaxlitlash',      kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('ceil()') },
  { label: 'floor', detail: '.floor() → Int — Pastga yaxlitlash',       kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('floor()') },
  { label: 'clamp', detail: '.clamp(min, max) → Number — Oraliq chegara', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('clamp(${1:min}, ${2:max})') },
];

const ARRAY_METHODS = [
  { label: 'push',     detail: '.push(val) — Element qo\'shish',         kind: vscode.CompletionItemKind.Method,   insertText: new vscode.SnippetString('push(${1:value})') },
  { label: 'pop',      detail: '.pop() — Oxirgi elementni olish',        kind: vscode.CompletionItemKind.Method,   insertText: new vscode.SnippetString('pop()') },
  { label: 'join',     detail: '.join(sep) → String — Birlashtirish',    kind: vscode.CompletionItemKind.Method,   insertText: new vscode.SnippetString('join(${1:", "})') },
  { label: 'slice',    detail: '.slice(start, end) → Array — Qism kesish', kind: vscode.CompletionItemKind.Method, insertText: new vscode.SnippetString('slice(${1:start}, ${2:end})') },
  { label: 'length',   detail: '.length → Int — Massiv uzunligi',        kind: vscode.CompletionItemKind.Property, insertText: 'length' },
  { label: 'contains', detail: '.contains(val) → Boolean — Mavjudligi',  kind: vscode.CompletionItemKind.Method,   insertText: new vscode.SnippetString('contains(${1:value})') },
];


// ============================================================
// Snippet items
// ============================================================
function makeSnippetItems() {
  return [
    { label: 'fn',    detail: 'fn — Funksiya shablon',          kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('fn ${1:name}(${2:param}: ${3:Type}): ${4:Void} {\n\t${0}\n}'), sortText: '0_fn' },
    { label: 'fnx',   detail: 'fnx — Expression-body funksiya', kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('fn ${1:name}(${2:param}: ${3:Type}): ${4:Type} => ${0}'),     sortText: '0_fnx' },
    { label: 'class', detail: 'class — Klass shablon',          kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('class ${1:Name}(var ${2:field}: ${3:String}) {\n\tfn ${4:method}() {\n\t\t${0}\n\t}\n}'), sortText: '0_class' },
    { label: 'for',   detail: 'for — for-in sikl shablon',      kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('for (${1:item} in ${2:collection}) {\n\t${0}\n}'),             sortText: '0_for' },
    { label: 'forr',  detail: 'forr — Diapazon sikli shablon',  kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('for (${1:i} in ${2:0}..${3:10}) {\n\t${0}\n}'),              sortText: '0_forr' },
    { label: 'if',    detail: 'if — Shartli ibora',             kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('if (${1:condition}) {\n\t${0}\n}'),                           sortText: '0_if' },
    { label: 'ife',   detail: 'ife — if-else shablon',          kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('if (${1:condition}) {\n\t${2}\n} else {\n\t${0}\n}'),         sortText: '0_ife' },
    { label: 'while', detail: 'while — while sikl shablon',     kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('while (${1:condition}) {\n\t${0}\n}'),                        sortText: '0_while' },
    { label: 'main',  detail: 'main — Asosiy funksiya shablon', kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('fn main() {\n\t${0}\n}'),                                    sortText: '0_main' },
    { label: 'new',   detail: 'new — Ob\'ekt yaratish shablon', kind: vscode.CompletionItemKind.Snippet, insertText: new vscode.SnippetString('new ${1:ClassName}(${0})'),                                  sortText: '0_new' },
  ];
}

// ============================================================
// Completion Provider
// ============================================================
function provideCompletions(document, position, token, context) {
  const linePrefix = document.lineAt(position).text.substring(0, position.character);

  if (context.triggerCharacter === '.' || linePrefix.match(/\.\s*$/)) {
    const seen = new Set();
    const dotItems = [];
    for (const m of [...STRING_METHODS, ...NUMBER_METHODS, ...ARRAY_METHODS]) {
      if (seen.has(m.label)) continue;
      seen.add(m.label);
      const item = new vscode.CompletionItem(m.label, m.kind);
      item.detail = m.detail;
      if (m.insertText) item.insertText = m.insertText;
      if (m.documentation) item.documentation = m.documentation;
      dotItems.push(item);
    }
    return dotItems;
  }

  const items = [];

  for (const kw of KEYWORDS) {
    const item = new vscode.CompletionItem(kw.label, kw.kind);
    item.detail = kw.detail;
    item.sortText = 'b_' + kw.label;
    items.push(item);
  }
  for (const t of TYPES) {
    const item = new vscode.CompletionItem(t.label, t.kind);
    item.detail = t.detail;
    item.sortText = 'c_' + t.label;
    items.push(item);
  }
  for (const b of BUILTINS) {
    const item = new vscode.CompletionItem(b.label, b.kind);
    item.detail = b.detail;
    if (b.insertText) item.insertText = b.insertText;
    if (b.documentation) item.documentation = b.documentation;
    item.sortText = 'a_' + b.label;
    items.push(item);
  }
  for (const sn of makeSnippetItems()) {
    const item = new vscode.CompletionItem(sn.label, sn.kind);
    item.detail = sn.detail;
    item.insertText = sn.insertText;
    if (sn.documentation) item.documentation = sn.documentation;
    if (sn.sortText) item.sortText = sn.sortText;
    items.push(item);
  }

  return items;
}

// ============================================================
// Hover Provider
// ============================================================
function provideHover(document, position) {
  const word = document.getText(document.getWordRangeAtPosition(position));
  if (!word) return null;

  const builtin = BUILTINS.find(b => b.label === word);
  if (builtin) {
    return new vscode.Hover([
      new vscode.MarkdownString(`**Flow Built-in** — \`${builtin.detail}\``),
      builtin.documentation || '',
    ]);
  }
  const keyword = KEYWORDS.find(k => k.label === word);
  if (keyword) return new vscode.Hover(new vscode.MarkdownString(`**Flow Keyword** — ${keyword.detail}`));

  const type = TYPES.find(t => t.label === word);
  if (type) return new vscode.Hover(new vscode.MarkdownString(`**Flow Type** — ${type.detail}`));

  return null;
}

// ============================================================
// Diagnostics — Statik Tahlil (Real-time qizil chiziqlar)
// ============================================================

/** Python yordamida statik tahlil o'tkazish va JSON olish */
function runFlowCheck(filePath) {
  return new Promise((resolve) => {
    // Python buyruqni topish (flow cmd yoki python -m src.cli)
    const pythonCmds = ['python', 'python3', 'py'];

    // Flow-Lang loyiha papkasini topish (extension.js ning joylashuvi bilan)
    // Global extension: %USERPROFILE%/.vscode/extensions/flow-language-tools/src/extension.js
    // Loyiha papkasi: FLOW_PROJECT_PATH env yoki workspace folder
    const workspaceFolders = vscode.workspace.workspaceFolders;
    let projectPath = null;

    if (workspaceFolders) {
      for (const folder of workspaceFolders) {
        const candidate = path.join(folder.uri.fsPath, 'src', 'cli.py');
        if (fs.existsSync(candidate)) {
          projectPath = folder.uri.fsPath;
          break;
        }
      }
    }

    if (!projectPath) {
      resolve([]);
      return;
    }

    // python -m src.cli --check <file>
    const python = process.platform === 'win32' ? 'python' : 'python3';
    const result = spawnSync(
      python,
      ['-m', 'src.cli', '--check', filePath],
      {
        cwd: projectPath,
        encoding: 'utf-8',
        timeout: 5000,
      }
    );

    if (result.error || result.status === null) {
      resolve([]);
      return;
    }

    try {
      const stdout = (result.stdout || '').trim();
      if (!stdout || stdout === '[]') {
        resolve([]);
        return;
      }
      const diags = JSON.parse(stdout);
      resolve(Array.isArray(diags) ? diags : []);
    } catch (e) {
      resolve([]);
    }
  });
}

/** JSON diagnostikalarni VS Code Diagnostic formatiga o'girish */
function toDiagnostics(rawDiags, document) {
  return rawDiags.map(d => {
    const line   = Math.max(0, (d.line || 1) - 1);   // 0-indexed
    const colStart = d.colStart || 0;
    const colEnd   = d.colEnd   || colStart + 1;

    // Qator matnidan to'g'ri range olish
    let range;
    try {
      const lineText = document.lineAt(line).text;
      const safeEnd  = Math.min(colEnd, lineText.length);
      const safeStart = Math.min(colStart, lineText.length);
      range = new vscode.Range(line, safeStart, line, safeEnd || safeStart + 1);
    } catch {
      range = new vscode.Range(line, 0, line, 1);
    }

    const severity =
      d.severity === 'error'   ? vscode.DiagnosticSeverity.Error   :
      d.severity === 'warning' ? vscode.DiagnosticSeverity.Warning :
                                 vscode.DiagnosticSeverity.Information;

    const diag = new vscode.Diagnostic(range, d.message, severity);
    diag.source = 'Flow';
    return diag;
  });
}

/** Hujjat o'zgarganda diagnostikalarni yangilash */
async function updateDiagnostics(document, collection) {
  if (!document || document.languageId !== 'flow') {
    return;
  }
  const filePath = document.uri.fsPath;
  if (!filePath.endsWith('.flw')) {
    collection.delete(document.uri);
    return;
  }

  try {
    const rawDiags = await runFlowCheck(filePath);
    const vsDiags  = toDiagnostics(rawDiags, document);
    collection.set(document.uri, vsDiags);
  } catch (e) {
    collection.set(document.uri, []);
  }
}

// ============================================================
// Extension aktivatsiyasi
// ============================================================
function activate(context) {
  console.log('Flow Language Tools v0.2.0 faollashdi!');

  // --- Diagnostic Collection ---
  const diagnosticCollection = vscode.languages.createDiagnosticCollection('flow');
  context.subscriptions.push(diagnosticCollection);

  // Hozir ochiq bo'lgan barcha .flw fayllarni tekshirish
  if (vscode.window.activeTextEditor) {
    updateDiagnostics(vscode.window.activeTextEditor.document, diagnosticCollection);
  }

  // Fayl ochilganda
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(doc => {
      updateDiagnostics(doc, diagnosticCollection);
    })
  );

  // Fayl tahrirlanganda (kichik kechikish bilan — debounce)
  let debounceTimer = null;
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument(event => {
      if (event.document.languageId !== 'flow') return;
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        updateDiagnostics(event.document, diagnosticCollection);
      }, 800); // 800ms kechikish
    })
  );

  // Fayl saqlanganda — darhol tekshirish
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(doc => {
      if (doc.languageId === 'flow') {
        updateDiagnostics(doc, diagnosticCollection);
      }
    })
  );

  // Fayl yopilganda diagnostikalarni tozalash
  context.subscriptions.push(
    vscode.workspace.onDidCloseTextDocument(doc => {
      diagnosticCollection.delete(doc.uri);
    })
  );

  // --- Completion Provider ---
  const completionProvider = vscode.languages.registerCompletionItemProvider(
    { language: 'flow', scheme: 'file' },
    { provideCompletionItems: provideCompletions },
    '.',
  );
  context.subscriptions.push(completionProvider);

  // --- Hover Provider ---
  const hoverProvider = vscode.languages.registerHoverProvider(
    { language: 'flow', scheme: 'file' },
    { provideHover },
  );
  context.subscriptions.push(hoverProvider);

  // --- Status Bar ---
  const runStatusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  runStatusBar.text = '$(play) Flow Run';
  runStatusBar.tooltip = 'Joriy Flow faylni ishga tushirish (Ctrl+F5)';
  runStatusBar.command = 'flow.runCurrentFile';
  runStatusBar.show();
  context.subscriptions.push(runStatusBar);

  // Error count status bar
  const errorBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 99);
  context.subscriptions.push(errorBar);

  // Diagnostikalar o'zgarganda error count ni yangilash
  context.subscriptions.push(
    vscode.languages.onDidChangeDiagnostics(e => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || editor.document.languageId !== 'flow') {
        errorBar.hide();
        return;
      }
      const diags = vscode.languages.getDiagnostics(editor.document.uri);
      const errors   = diags.filter(d => d.severity === vscode.DiagnosticSeverity.Error).length;
      const warnings = diags.filter(d => d.severity === vscode.DiagnosticSeverity.Warning).length;

      if (errors === 0 && warnings === 0) {
        errorBar.text = '$(check) Flow OK';
        errorBar.backgroundColor = undefined;
        errorBar.tooltip = 'Flow: Xatolar yo\'q';
      } else {
        const parts = [];
        if (errors > 0)   parts.push(`$(error) ${errors} xato`);
        if (warnings > 0) parts.push(`$(warning) ${warnings} ogohlantirish`);
        errorBar.text = parts.join('  ');
        errorBar.backgroundColor = errors > 0
          ? new vscode.ThemeColor('statusBarItem.errorBackground')
          : new vscode.ThemeColor('statusBarItem.warningBackground');
        errorBar.tooltip = `Flow diagnostikasi: ${errors} xato, ${warnings} ogohlantirish`;
      }
      errorBar.show();
    })
  );

  // --- Run Command ---
  const runCommand = vscode.commands.registerCommand('flow.runCurrentFile', () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage('Flow: Faol redaktor topilmadi!');
      return;
    }
    const filePath = editor.document.uri.fsPath;
    if (!filePath.endsWith('.flw')) {
      vscode.window.showWarningMessage('Flow: Faqat .flw fayllarini ishga tushirish mumkin!');
      return;
    }

    // Avval saqlash
    editor.document.save();

    // Loyihaning cli.py manzili
    const cliPath = "C:\\Users\\User\\Flow-Lang\\src\\cli.py";
    const fileDir = path.dirname(filePath);

    // Mavjud "Flow Run" terminalini topish yoki yangisini yaratish
    let terminal = vscode.window.terminals.find(t => t.name === 'Flow Run');
    if (!terminal) {
      terminal = vscode.window.createTerminal({ name: 'Flow Run', cwd: fileDir });
    }
    terminal.show();

    // Istalgan katalogdagi faylni to'g'ri verbose rejimda ishga tushirish
    terminal.sendText(`python "${cliPath}" "${filePath}" -v`);
  });
  context.subscriptions.push(runCommand);

  // --- Check Command (qo'lda) ---
  const checkCommand = vscode.commands.registerCommand('flow.checkCurrentFile', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== 'flow') {
      vscode.window.showWarningMessage('Flow: .flw fayli ochilmagan!');
      return;
    }
    await updateDiagnostics(editor.document, diagnosticCollection);
    const diags = vscode.languages.getDiagnostics(editor.document.uri);
    if (diags.length === 0) {
      vscode.window.showInformationMessage('✅ Flow: Xatolar topilmadi!');
    } else {
      const errors = diags.filter(d => d.severity === 0).length;
      vscode.window.showWarningMessage(`⚠️ Flow: ${errors} xato topildi. Problems panelini tekshiring.`);
    }
  });
  context.subscriptions.push(checkCommand);
}

function deactivate() {}

module.exports = { activate, deactivate };
