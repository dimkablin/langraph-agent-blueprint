import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const srcRoot = join(root, "frontend", "src");

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function sourceFiles(dir = srcRoot) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    if (/\.(ts|tsx|css)$/.test(entry.name)) return [path];
    return [];
  });
}

function sourceText() {
  return sourceFiles()
    .map((path) => `\n// ${relative(srcRoot, path)}\n${readFileSync(path, "utf8")}`)
    .join("\n");
}

function nonNoneBoxShadowValues(css) {
  return [...css.matchAll(/box-shadow:\s*([^;]+);/g)]
    .map((match) => match[1].trim())
    .filter((value) => value !== "none");
}

function withoutLiquidGlassSidebarRules(css) {
  return css.replace(/\.app-shell-sidebar-glass \.runtime-sidebar-panel(?:\:\:before|\:\:after)?\s*\{[^}]*\}/g, "");
}

test("TypeScript runtime frontend entrypoint is active", () => {
  const index = readFileSync(join(root, "frontend", "index.html"), "utf8");
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const chatHook = readFileSync(join(srcRoot, "hooks", "useRuntimeChat.ts"), "utf8");

  assert.match(index, /\/src\/main\.tsx/);
  assert.match(app, /useRuntimeChat/);
  assert.match(chatHook, /streamChat/);
  assert.match(app, /PermissionPanel/);
  assert.match(app, /RuntimeSidebar/);
  assert.match(app, /context=\{runtimeState\.context\}/);
  assert.match(app, /RuntimeDrawer/);
});

test("App composes hooks instead of owning runtime orchestration", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");

  assert.match(app, /useRuntimeChat/);
  assert.match(app, /useRuntimeRegistries/);
  assert.match(app, /useRuntimeSessions/);
  assert.match(app, /useRuntimeStatus/);
  assert.doesNotMatch(app, /streamChat|sendApproval|fetchCommands|fetchSessions|fetchRuntimeStatus/);
  assert.doesNotMatch(app, /useEffect|useRef/);
});

test("frontend uses graph-facing backend endpoints only", () => {
  const text = sourceText();
  const packageJson = readFileSync(join(root, "frontend", "package.json"), "utf8");

  assert.match(text, /\/chat\/stream/);
  assert.match(text, /\/approval/);
  assert.match(text, /\/sessions/);
  assert.match(text, /\/commands/);
  assert.match(text, /\/skills/);
  assert.match(text, /\/tools/);
  assert.doesNotMatch(text, /\/tools\/execute/);
  assert.doesNotMatch(text, /query\/stream/);
  assert.doesNotMatch(text, /luxms|otp-login|login_as/i);
  assert.doesNotMatch(packageJson, /@tabler\/icons-react/);
  assert.doesNotMatch(packageJson, /lucide-react/);
  assert.doesNotMatch(text, /from "lucide-react"|from 'lucide-react'/);
  assert.doesNotMatch(text, /@tabler\/icons-react/);
  assert.doesNotMatch(text, /@tabler\/icons-react\/dist\/cjs/);
});

test("runtime API and reducer layers are separated from components", () => {
  const api = readFileSync(join(srcRoot, "api", "stream.ts"), "utf8");
  const reducer = readFileSync(join(srcRoot, "runtime", "reducer.ts"), "utf8");
  const componentFiles = sourceFiles(join(srcRoot, "components"));
  const components = componentFiles.map((path) => readFileSync(path, "utf8")).join("\n");

  assert.match(api, /fetch\(apiUrl\("\/chat\/stream"\)/);
  assert.match(reducer, /applyRuntimeEvent/);
  assert.doesNotMatch(components, /fetch\(/);
  assert.doesNotMatch(components, /\/chat|\/approval|\/tools/);
});

test("backend frontend contract still exposes typed streaming, sessions, and status routes", () => {
  const schemas = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "schemas.py"), "utf8");
  const server = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "server.py"), "utf8");
  const chatRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_chat.py"), "utf8");
  const sessionRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_sessions.py"), "utf8");
  const statusRoutes = readFileSync(join(root, "src", "langgraph_agent_blueprint", "api", "routes_status.py"), "utf8");

  assert.match(schemas, /class RuntimeEventDTO/);
  assert.match(schemas, /class StreamFrame/);
  assert.match(schemas, /class PermissionDecisionDTO/);
  assert.match(schemas, /class SessionDetailDTO/);
  assert.match(schemas, /class ContextStateDTO/);
  assert.match(chatRoutes, /text\/event-stream/);
  assert.match(sessionRoutes, /\/sessions\/\{session_id\}\/context/);
  assert.match(sessionRoutes, /\/sessions\/\{session_id\}\/child-runs/);
  assert.match(statusRoutes, /\/config\/explain/);
  assert.match(statusRoutes, /\/observability/);
  assert.doesNotMatch(server, /@api\.get\("\/(commands|skills|tools)"\)/);
});

test("chat controls are icon-triggered and message avatars are removed", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const header = readFileSync(join(srcRoot, "components", "layout", "StatusHeader.tsx"), "utf8");
  const sidebar = readFileSync(join(srcRoot, "components", "layout", "RuntimeSidebar.tsx"), "utf8");
  const bubble = readFileSync(join(srcRoot, "components", "chat", "MessageBubble.tsx"), "utf8");

  assert.doesNotMatch(app, /activeDrawer === "chats"/);
  assert.doesNotMatch(app, /title="Чаты"/);
  assert.match(app, /title="Commands \/ Skills \/ Tools"/);
  assert.match(sidebar, /onOpenSettings/);
  assert.match(sidebar, /IconSettings/);
  assert.match(header, /IconLayoutSidebarLeftExpand/);
  assert.match(header, /IconPlus/);
  assert.match(header, /IconHelpCircle/);
  assert.match(header, /data-tooltip="Боковая панель"/);
  assert.match(header, /data-tooltip="Новый чат"/);
  assert.doesNotMatch(header, /title="Боковая панель"|title="Новый чат"/);
  assert.doesNotMatch(header, /Settings/);
  assert.doesNotMatch(header, /onOpenSettings/);
  assert.doesNotMatch(header, /MessageSquare/);
  assert.doesNotMatch(header, /Bot|brand-lockup|brand-mark|langgraph-agent-blueprint|Thin runtime frontend/);
  assert.doesNotMatch(header, /compactId|Radio|CircleAlert|CircleCheck/);
  assert.doesNotMatch(header, /session \{|thread \{|apiStatus|status\}/);
  assert.doesNotMatch(header, />Чаты<\/span>/);
  assert.doesNotMatch(bubble, /avatar/);
  assert.doesNotMatch(bubble, /<Bot|<User/);
});

test("app icons mirror the donor lucide glyphs without adding a runtime icon dependency", () => {
  const icons = readFileSync(join(srcRoot, "icons.ts"), "utf8");
  const contextMeter = readFileSync(join(srcRoot, "components", "chat", "ComposerContextMeter.tsx"), "utf8");
  const iconBodies = [...icons.matchAll(/export const Icon\w+ = makeIcon\(\[([\s\S]*?)\]\);/g)];
  const packageJson = readFileSync(join(root, "frontend", "package.json"), "utf8");

  assert.match(icons, /lucide-react v0\.487\.0/);
  assert.match(icons, /strokeWidth = 2/);
  assert.ok(iconBodies.length >= 18);
  assert.match(icons, /IconArrowUp = makeIcon\(\[\s*\{ d: "M12 19V5" \},\s*\{ d: "m5 12 7-7 7 7" \}/);
  assert.match(icons, /IconSettings = makeIcon\(\[\s*\{ d: "M20 7h-9" \}/);
  assert.match(icons, /IconMessages = makeIcon\(\[\s*\{ d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5/);
  assert.match(icons, /IconCopy = makeIcon\(\[\s*\{ x: 8, y: 8, width: 14, height: 14, rx: 2/);
  assert.match(icons, /IconSparkles = makeIcon\(\[\s*\{ d: "M9\.937 15\.5/);
  assert.doesNotMatch(packageJson, /lucide-react/);
  assert.doesNotMatch(icons, /from "lucide-react"|from 'lucide-react'/);
  assert.match(contextMeter, /const radius = 6/);
  assert.match(contextMeter, /viewBox="0 0 16 16"/);
});

test("header action buttons are borderless icon-only controls", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /\.app-header\s*\{[^}]*border-bottom:\s*0/);
  assert.match(styles, /\.app-header\s*\{[^}]*background:\s*color-mix\(in oklab,\s*var\(--surface-0\) 94%,\s*transparent\)/);
  assert.match(styles, /\.app-header\s*\{[^}]*min-height:\s*48px/);
  assert.match(styles, /\.app-header\s*\{[^}]*padding:\s*0 14px/);
  assert.match(styles, /\.app-header\s*\{[^}]*justify-content:\s*space-between/);
  assert.match(styles, /\.header-leading\s*\{[^}]*display:\s*flex/);
  assert.match(styles, /\.icon-button\s*\{[^}]*border:\s*0/);
  assert.match(styles, /\.icon-button\s*\{[^}]*width:\s*32px/);
  assert.match(styles, /\.icon-button\s*\{[^}]*height:\s*32px/);
  assert.match(styles, /\.icon-button\s*\{[^}]*background:\s*transparent/);
  assert.match(styles, /\.icon-button\s*\{[^}]*padding:\s*0/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*content:\s*attr\(data-tooltip\)/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*background:\s*var\(--card-elevated\)/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*max-width:\s*min\(220px,\s*calc\(100vw - 24px\)\)/);
  assert.match(styles, /\[data-tooltip\]\[data-tooltip-align="start"\]::after/);
  assert.match(styles, /\[data-tooltip\]\[data-tooltip-align="end"\]::after/);
  assert.match(styles, /\[data-tooltip\]:hover::after/);
  assert.match(styles, /\.icon-button:hover,[\s\S]*\.icon-button:focus-visible\s*\{[^}]*background:\s*var\(--hover-surface\)/);
  assert.doesNotMatch(styles, /\.icon-button\s*\{[^}]*border:\s*1px/);
  assert.doesNotMatch(styles, /brand-lockup|brand-mark/);
});

test("scrollbars are thin with transparent tracks and seventy-percent transparent thumbs", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /--scrollbar-track:\s*transparent/);
  assert.match(styles, /--scrollbar-thumb:\s*color-mix\(in oklab,\s*var\(--foreground\) 30%,\s*transparent\)/);
  assert.match(styles, /scrollbar-width:\s*thin/);
  assert.match(styles, /\*::-webkit-scrollbar\s*\{[^}]*width:\s*6px/);
  assert.match(styles, /\*::-webkit-scrollbar\s*\{[^}]*height:\s*6px/);
  assert.match(styles, /\*::-webkit-scrollbar-track\s*\{[^}]*background:\s*var\(--scrollbar-track\)/);
  assert.match(styles, /\*::-webkit-scrollbar-thumb\s*\{[^}]*background:\s*var\(--scrollbar-thumb\)/);
});

test("message metadata renders outside the message block and appears on hover", () => {
  const bubble = readFileSync(join(srcRoot, "components", "chat", "MessageBubble.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(bubble, /MessageMeta/);
  assert.match(bubble, /Copy message/);
  assert.match(bubble, /navigator\.clipboard\.writeText/);
  assert.match(bubble, /const messageClass = isUser/);
  assert.match(bubble, /<div className=\{messageClass\}>[\s\S]*<\/div>\s*<MessageMeta/);
  assert.doesNotMatch(styles, /\.message-card time/);
  assert.match(styles, /\.message-meta\s*\{[^}]*opacity:\s*0/);
  assert.match(styles, /\.message-meta\s*\{[^}]*pointer-events:\s*none/);
  assert.match(styles, /\.message-row:hover \.message-meta/);
  assert.match(styles, /\.message-copy-button/);
});

test("context compaction renders as a non-copyable timeline separator", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const reducer = readFileSync(join(srcRoot, "runtime", "reducer.ts"), "utf8");
  const messageList = readFileSync(join(srcRoot, "components", "chat", "MessageList.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(reducer, /compact_finished/);
  assert.match(reducer, /compact_started/);
  assert.match(reducer, /appendTimelineSeparator/);
  assert.match(reducer, /completeTimelineSeparator/);
  assert.match(reducer, /isCompactionStatusResponse/);
  assert.match(reducer, /isVisibleMessageDto/);
  assert.match(reducer, /Compacted prior context:/);
  assert.match(reducer, /detail\.messages\.filter\(isVisibleMessageDto\)/);
  assert.match(app, /items=\{runtimeState\.timeline\}/);
  assert.match(messageList, /ChatTimelineItem/);
  assert.match(messageList, /item\.kind === "separator"/);
  assert.match(messageList, /message-separator-running/);
  assert.match(messageList, /message-separator/);
  assert.doesNotMatch(messageList, /MessageSeparator[\s\S]*MessageMeta/);
  assert.match(styles, /\.message-separator\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1fr\)\s*auto\s*minmax\(0,\s*1fr\)/);
  assert.match(styles, /@keyframes compact-separator-blink/);
  assert.match(styles, /\.message-separator-running \.message-separator-label\s*\{[^}]*animation:\s*compact-separator-blink/);
  assert.match(styles, /\.message-separator::before,/);
  assert.match(styles, /\.message-separator-label/);
});

test("technical payloads render as terminal-like message cards", () => {
  const bubble = readFileSync(join(srcRoot, "components", "chat", "MessageBubble.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(bubble, /isTechnicalMessage/);
  assert.match(bubble, /message\.role === "user"/);
  assert.match(bubble, /message-card-technical/);
  assert.match(styles, /\.message-card-technical\s*\{[^}]*font-family:\s*var\(--font-mono\)/);
  assert.match(styles, /\.message-card-technical\s*\{[^}]*background:\s*var\(--surface-terminal\)/);
  assert.match(styles, /\.message-card-technical\s*\{[^}]*color:\s*var\(--terminal-foreground\)/);
  assert.match(styles, /\.message-card-technical\s*\{[^}]*border:\s*0/);
});

test("assistant messages render markdown through a safe AST renderer", () => {
  const markdownBlock = readFileSync(join(srcRoot, "components", "common", "MarkdownBlock.tsx"), "utf8");
  const markdownParser = readFileSync(join(srcRoot, "components", "common", "markdown.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(markdownBlock, /parseMarkdown/);
  assert.match(markdownBlock, /renderBlock/);
  assert.match(markdownBlock, /renderInline/);
  assert.match(markdownBlock, /target="_blank"/);
  assert.match(markdownParser, /isSafeLinkHref/);
  assert.doesNotMatch(markdownBlock, /dangerouslySetInnerHTML/);
  assert.match(styles, /\.markdown-block h1,/);
  assert.match(styles, /\.markdown-block ul,/);
  assert.match(styles, /\.markdown-block pre\s*\{[^}]*overflow-x:\s*auto/);
  assert.match(styles, /\.markdown-block a\s*\{[^}]*color:\s*var\(--primary\)/);
});

test("main page keeps only chat while registries live behind the help drawer", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /EventTimeline/);
  assert.match(app, /activities=\{runtimeState\.activities\}/);
  assert.doesNotMatch(app, /side-panel/);
  assert.match(app, /activeDrawer === "help"/);
  assert.doesNotMatch(app, /activeDrawer === "chats"/);
  assert.match(app, /<RegistryPanel commands=\{commands\} skills=\{skills\} tools=\{tools\}/);
  assert.doesNotMatch(styles, /side-panel/);
  assert.doesNotMatch(styles, /runtime-workspace/);
});

test("new chat starts with centered composer and task examples", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const examples = readFileSync(join(srcRoot, "components", "chat", "WelcomePromptExamples.tsx"), "utf8");
  const messageList = readFileSync(join(srcRoot, "components", "chat", "MessageList.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /isNewChat/);
  assert.match(app, /Что нужно сделать\?/);
  assert.match(app, /WelcomePromptExamples/);
  assert.match(app, /WELCOME_PROMPT_EXAMPLES/);
  assert.doesNotMatch(app, /approve\/reject/);
  assert.match(app, /variant="welcome"/);
  assert.match(composer, /variant\?: "dock" \| "welcome"/);
  assert.match(composer, /composer-welcome/);
  assert.match(composer, /Спросите у агента о чем угодно\. Используйте @ для плагинов или \/ для комманд/);
  assert.match(composer, /Напишите агенту еще что-нибудь/);
  assert.match(examples, /WelcomePromptExample/);
  assert.match(examples, /IconGitCompare/);
  assert.match(examples, /IconListCheck/);
  assert.match(examples, /IconBlocks/);
  assert.doesNotMatch(examples, /FileSearch|Puzzle|Wrench|GitBranch/);
  assert.match(examples, /onSelect\(example\.prompt\)/);
  assert.doesNotMatch(messageList, /Runtime ready/);
  assert.match(styles, /\.chat-column-welcome\s*\{[^}]*justify-content:\s*center/);
  assert.match(styles, /\.welcome-chat\s*\{[^}]*justify-content:\s*center/);
  assert.match(styles, /\.welcome-chat h1\s*\{[^}]*font-size:\s*clamp/);
  assert.match(styles, /\.composer-welcome\s*\{[^}]*position:\s*relative/);
  assert.match(styles, /\.welcome-examples\s*\{[^}]*width:\s*min\(720px,\s*100%\)/);
  assert.match(styles, /\.welcome-examples\s*\{[^}]*margin-top:\s*22px/);
  assert.match(styles, /\.welcome-examples\s*\{[^}]*padding-inline:\s*8px/);
  assert.match(styles, /\.welcome-example\s*\{[^}]*border-top:\s*1px solid/);
  assert.match(styles, /\.welcome-example:first-child\s*\{[^}]*border-top:\s*0/);
  assert.match(styles, /\.welcome-example:hover,[\s\S]*\.welcome-example:focus-visible\s*\{[^}]*background:\s*transparent/);
  assert.match(styles, /\.welcome-example:hover,[\s\S]*\.welcome-example:focus-visible\s*\{[^}]*color:\s*var\(--foreground\)/);
});

test("runtime sidebar is a persistent layout block toggled by the header button", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const header = readFileSync(join(srcRoot, "components", "layout", "StatusHeader.tsx"), "utf8");
  const sidebar = readFileSync(join(srcRoot, "components", "layout", "RuntimeSidebar.tsx"), "utf8");
  const liquidGlassFilters = readFileSync(join(srcRoot, "components", "common", "LiquidGlassFilterDefs.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /sidebarOpen/);
  assert.match(app, /app-shell app-shell-sidebar-open/);
  assert.match(app, /themeConfigForPreferences/);
  assert.match(app, /LiquidGlassFilterDefs/);
  assert.match(liquidGlassFilters, /id="lg-sidebar-distortion"/);
  assert.match(liquidGlassFilters, /feTurbulence/);
  assert.match(liquidGlassFilters, /type="fractalNoise"/);
  assert.match(liquidGlassFilters, /feGaussianBlur/);
  assert.match(liquidGlassFilters, /feDisplacementMap/);
  assert.match(liquidGlassFilters, /scale=\{18\}/);
  assert.match(app, /app-shell-sidebar-glass/);
  assert.match(app, /<RuntimeSidebar[\s\S]*<div className="app-main">[\s\S]*<StatusHeader/);
  assert.match(app, /<RuntimeSidebar/);
  assert.doesNotMatch(app, /app-body app-body-sidebar-open/);
  assert.doesNotMatch(app, /<SessionsPanel/);
  assert.doesNotMatch(app, /setSidebarOpen\(false\)/);
  assert.match(header, /aria-label="Боковая панель"/);
  assert.match(header, /aria-label="Новый чат"/);
  assert.doesNotMatch(sidebar, /runtime-sidebar-backdrop/);
  assert.doesNotMatch(sidebar, /sidebar-close-button/);
  assert.match(sidebar, /runtime-sidebar-panel/);
  assert.match(sidebar, /runtime-sidebar-gap/);
  assert.match(sidebar, /Новый чат/);
  assert.match(sidebar, /Поиск/);
  assert.match(sidebar, /Плагины/);
  assert.match(sidebar, /Чаты/);
  assert.doesNotMatch(sidebar, /Просто чаты/);
  assert.doesNotMatch(sidebar, /MessageCircle/);
  assert.doesNotMatch(sidebar, /<small>\{filteredSessions\.length\}<\/small>/);
  assert.doesNotMatch(sidebar, /slice\(0,\s*18\)/);
  assert.match(sidebar, /session\.title/);
  assert.doesNotMatch(sidebar, /session\.preview/);
  assert.doesNotMatch(sidebar, /message_count/);
  assert.match(sidebar, /Настройки/);
  assert.match(sidebar, /SessionListItemDTO/);
  assert.match(styles, /\.app-shell\s*\{[^}]*flex-direction:\s*row/);
  assert.match(styles, /body\s*\{[^}]*overflow:\s*hidden/);
  assert.match(styles, /\.app-shell\s*\{[^}]*height:\s*100vh/);
  assert.match(styles, /\.app-shell\s*\{[^}]*overflow:\s*hidden/);
  assert.match(styles, /\.app-main\s*\{[^}]*flex:\s*1/);
  assert.match(styles, /\.app-main\s*\{[^}]*flex-direction:\s*column/);
  assert.match(styles, /\.app-body\s*\{[^}]*display:\s*flex/);
  assert.doesNotMatch(styles, /\.runtime-sidebar-backdrop/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*flex:\s*0 0 280px/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*height:\s*100vh/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*overflow:\s*hidden/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*position:\s*relative/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*padding:\s*0/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar::before/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar::after/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*width:\s*calc\(100% - 8px\)/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*height:\s*100%/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*min-height:\s*0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*position:\s*relative/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*isolation:\s*isolate/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*border-right:\s*0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*border-radius:\s*0 var\(--control-radius\) var\(--control-radius\) 0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*margin-right:\s*0/);
  assert.match(styles, /\.runtime-sidebar-gap\s*\{[^}]*flex:\s*0 0 8px/);
  assert.match(styles, /\.runtime-sidebar-gap\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.runtime-sidebar-gap\s*\{[^}]*z-index:\s*2/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*--liquid-wallpaper-accent:\s*var\(--primary\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*--liquid-wallpaper-secondary:\s*var\(--skill\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*var\(--liquid-wallpaper-accent\) 34%/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*var\(--liquid-wallpaper-accent\) 72%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*var\(--liquid-wallpaper-secondary\) 28%/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*var\(--liquid-wallpaper-secondary\) 62%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*radial-gradient\(\s*ellipse at 14% 8%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*radial-gradient\(\s*ellipse at 92% 30%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*linear-gradient\(\s*118deg/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*repeating-radial-gradient/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*radial-gradient\(\s*ellipse at 96% 10%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*linear-gradient\(\s*180deg/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*box-shadow:\s*[^;]*inset -18px 0 34px/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*border-top:\s*1px/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*border-right-color/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*inset 1px 0 0/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*inset -1px 0 0/);
  assert.doesNotMatch(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*18px 0 42px/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*backdrop-filter:\s*blur\(34px\) saturate\(1\.24\) contrast\(1\.02\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*backdrop-filter:\s*url\("#lg-sidebar-distortion"\) blur\(34px\) saturate\(1\.24\) contrast\(1\.02\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*-webkit-backdrop-filter:\s*blur\(34px\) saturate\(1\.24\) contrast\(1\.02\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel\s*\{[^}]*-webkit-backdrop-filter:\s*url\("#lg-sidebar-distortion"\) blur\(34px\) saturate\(1\.24\) contrast\(1\.02\)/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel::before,\s*\.app-shell-sidebar-glass \.runtime-sidebar-panel::after\s*\{[^}]*content:\s*""/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel::before\s*\{[^}]*linear-gradient\(\s*90deg/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel::after\s*\{[^}]*radial-gradient\(\s*ellipse at 100% 16%/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel::after\s*\{[^}]*opacity:\s*0\.28/);
  assert.match(styles, /\.app-shell-sidebar-glass \.runtime-sidebar-panel > \*\s*\{[^}]*z-index:\s*1/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*flex:\s*1/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*--sidebar-chat-scrollbar-track:\s*transparent/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*--sidebar-chat-scrollbar-thumb:\s*color-mix\(in oklab,\s*var\(--foreground\) 30%,\s*transparent\)/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*overflow:\s*auto/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*scrollbar-width:\s*thin/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*scrollbar-color:\s*var\(--sidebar-chat-scrollbar-thumb\) var\(--sidebar-chat-scrollbar-track\)/);
  assert.match(styles, /\.runtime-sidebar-chat-list::-webkit-scrollbar\s*\{[^}]*width:\s*4px/);
  assert.match(styles, /\.runtime-sidebar-chat-list::-webkit-scrollbar-button\s*\{[^}]*display:\s*none/);
  assert.match(styles, /\.runtime-sidebar-chat-list::-webkit-scrollbar-track\s*\{[^}]*background:\s*var\(--sidebar-chat-scrollbar-track\)/);
  assert.doesNotMatch(styles, /\.runtime-sidebar-chat\.selected\s*\{[^}]*box-shadow:\s*inset 2px 0 0 var\(--primary\)/);
  assert.match(styles, /\.runtime-sidebar-bottom\s*\{[^}]*margin-top:\s*auto/);
});

test("codex theme v1 is applied to dark, light, and system themes", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");
  const settingsStyles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*color-scheme:\s*light/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-theme-id:\s*codex/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-theme-variant:\s*light/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-accent:\s*#0169cc/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-contrast:\s*45/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-ink:\s*#0d0d0d/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-surface:\s*#ffffff/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-diff-added:\s*#00a240/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-diff-removed:\s*#e02e2a/);
  assert.match(styles, /:root,\s*\.app-theme-light,\s*\.app-theme-system\s*\{[^}]*--codex-skill:\s*#751ed9/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*color-scheme:\s*dark/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-theme-id:\s*github/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-theme-variant:\s*dark/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-accent:\s*#1f6feb/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-contrast:\s*50/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-ink:\s*#e6edf3/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-surface:\s*#0d1117/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-background-surface:\s*color-mix\(in oklab,\s*var\(--codex-surface\) var\(--theme-sidebar-mix\),\s*var\(--codex-ink\)\)/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-sidebar-surface:\s*color-mix\(in oklab,\s*var\(--codex-surface\) 72%,\s*#000000\)/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-opaque-windows:\s*1/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-diff-added:\s*#3fb950/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-diff-removed:\s*#f85149/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--codex-skill:\s*#bc8cff/);
  assert.match(styles, /--background:\s*var\(--codex-background-surface\)/);
  assert.match(styles, /--surface-sidebar:\s*var\(--codex-sidebar-surface\)/);
  assert.match(styles, /--foreground:\s*var\(--codex-ink\)/);
  assert.match(styles, /--primary:\s*var\(--codex-accent\)/);
  assert.match(styles, /--success:\s*var\(--codex-diff-added\)/);
  assert.match(styles, /--danger:\s*var\(--codex-diff-removed\)/);
  assert.match(styles, /--skill:\s*var\(--codex-skill\)/);
  assert.match(styles, /--font-sans:\s*Inter,/);
  assert.match(styles, /--font-mono:\s*"Jetbrains Mono"/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--font-sans:\s*Geist,\s*Inter/);
  assert.match(styles, /\.app-theme-dark\s*\{[^}]*--font-mono:\s*"Geist Mono",\s*ui-monospace,\s*"SFMono-Regular"/);
  assert.match(styles, /--radius-sm:\s*4px/);
  assert.match(styles, /--radius-md:\s*8px/);
  assert.match(styles, /--radius-lg:\s*12px/);
  assert.doesNotMatch(settingsStyles, /\.app-theme-dark,[\s\S]*\.app-theme-light,[\s\S]*\.app-theme-system\s*\{[^}]*color-scheme:\s*light/);
  assert.match(styles, /--shadow-soft:\s*none/);
  assert.match(styles, /--shadow-panel:\s*none/);
  assert.match(styles, /--shadow-hairline:\s*none/);
  assert.match(styles, /--focus-ring:\s*none/);
  assert.match(styles, /--focus-outline:\s*color-mix\(in oklab,\s*var\(--border-strong\) 86%,\s*var\(--foreground\)\)/);
  assert.deepEqual(nonNoneBoxShadowValues(withoutLiquidGlassSidebarRules(`${styles}\n${settingsStyles}`)), []);
  assert.doesNotMatch(`${styles}\n${settingsStyles}`, /drop-shadow\(/);
  assert.doesNotMatch(`${styles}\n${settingsStyles}`, /inset 0 1px/);
  assert.doesNotMatch(`${styles}\n${settingsStyles}`, /--primary:\s*#8b93ff|--primary:\s*#4f5fc8|--figma-admin-green:\s*#00b473/);
});

test("technical runtime surfaces read like developer-tool panels", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");
  const settingsStyles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(styles, /\.permission-copy code,[\s\S]*\.activity-row pre\s*\{[^}]*background:\s*var\(--surface-terminal\)/);
  assert.match(styles, /\.permission-copy code,[\s\S]*\.activity-row pre\s*\{[^}]*color:\s*var\(--terminal-foreground\)/);
  assert.match(styles, /\.activity-running\s*\{[^}]*border-color:\s*color-mix\(in oklab,\s*var\(--secondary-info\) 38%,\s*var\(--border\)\)/);
  assert.match(styles, /\.status-good\s*\{[^}]*color:\s*var\(--success\)/);
  assert.match(styles, /\.runtime-sidebar-action svg\s*\{[^}]*color:\s*var\(--muted\)/);
  assert.match(styles, /\.send-button\s*\{[^}]*background:\s*color-mix\(in oklab,\s*var\(--primary\) 82%,\s*var\(--foreground\)\)/);
  assert.match(settingsStyles, /\.settings-badge-ok\s*\{[^}]*border-color:\s*color-mix\(in oklab,\s*var\(--success\) 34%,\s*transparent\)/);
});

test("mobile layout keeps sidebar overlay separate from page content", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");
  const settingsStyles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(styles, /@media \(max-width:\s*760px\)\s*\{[\s\S]*\.runtime-sidebar\s*\{[^}]*position:\s*fixed/);
  assert.match(styles, /@media \(max-width:\s*760px\)\s*\{[\s\S]*\.runtime-sidebar\s*\{[^}]*width:\s*min\(300px,\s*calc\(100vw - 28px\)\)/);
  assert.match(styles, /@media \(max-width:\s*760px\)\s*\{[\s\S]*\.runtime-sidebar\s*\{[^}]*z-index:\s*35/);
  assert.match(settingsStyles, /@media \(max-width:\s*680px\)\s*\{[\s\S]*\.settings-row-main\s*\{[^}]*grid-template-columns:\s*1fr/);
  assert.match(settingsStyles, /@media \(max-width:\s*680px\)\s*\{[\s\S]*\.settings-row-main strong\s*\{[^}]*justify-self:\s*start/);
});

test("chat presentation borrows widget width, message blocks, and floating composer", () => {
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /--ui-element-radius:\s*18px/);
  assert.match(styles, /--surface-radius:\s*var\(--ui-element-radius\)/);
  assert.match(styles, /--control-radius:\s*var\(--ui-element-radius\)/);
  assert.match(styles, /--radius:\s*var\(--ui-element-radius\)/);
  assert.match(styles, /--chat-block-radius:\s*var\(--ui-element-radius\)/);
  assert.match(styles, /--chat-column-width:\s*760px/);
  assert.match(styles, /--chat-edge-gap:\s*12px/);
  assert.match(styles, /\.icon-button\s*\{[^}]*border-radius:\s*var\(--control-radius\)/);
  assert.match(styles, /\.chat-column\s*\{[^}]*flex:\s*1 1 auto/);
  assert.match(styles, /\.chat-column\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.chat-column\s*\{[^}]*max-width:\s*none/);
  assert.match(styles, /\.chat-column\s*\{[^}]*margin:\s*0/);
  assert.match(styles, /\.chat-scroll\s*\{[^}]*padding:\s*22px 0 150px/);
  assert.match(styles, /\.chat-scroll\s*\{[^}]*scrollbar-gutter:\s*stable both-edges/);
  assert.match(styles, /\.message-list\s*\{[^}]*width:\s*min\(var\(--chat-column-width\),\s*calc\(100% - 24px\)\)/);
  assert.match(styles, /\.message-list\s*\{[^}]*margin:\s*0 auto/);
  assert.match(styles, /\.message-row\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.message-card\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*max-width:\s*min\(720px,\s*88%\)/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*border:\s*0/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*background:\s*color-mix\(in oklab,\s*var\(--card-elevated\)/);
  assert.doesNotMatch(styles, /\.message-card-user\s*\{[^}]*background:\s*var\(--primary\)/);
  assert.match(styles, /\.composer\s*\{[^}]*position:\s*sticky/);
  assert.match(styles, /\.composer\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.composer\s*\{[^}]*background:\s*transparent/);
  assert.match(styles, /\.composer\s*\{[^}]*padding:\s*0;/);
  assert.match(styles, /\.composer\s*\{[^}]*margin:\s*-96px 0 0/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*width:\s*min\(var\(--chat-column-width\),\s*calc\(100% - 24px\)\)/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*margin:\s*0 auto/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*background:\s*transparent/);
  assert.doesNotMatch(styles, /\.composer-surface\s*\{[^}]*background:\s*color-mix\(in oklab,\s*var\(--background\)/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*border-radius:\s*var\(--surface-radius\) var\(--surface-radius\) 0 0/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*overflow:\s*visible/);
  assert.doesNotMatch(styles, /\.composer-surface\s*\{[^}]*overflow:\s*hidden/);
  assert.match(styles, /\.composer-box\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.composer-box\s*\{[^}]*border:\s*1px solid transparent/);
  assert.match(styles, /\.composer-box\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.composer-box:focus-within\s*\{[^}]*border-color:\s*transparent/);
  assert.match(styles, /\.composer-box:focus-within\s*\{[^}]*box-shadow:\s*none/);
  assert.doesNotMatch(styles, /\.composer-box:focus-within\s*\{[^}]*var\(--primary\)/);
  assert.doesNotMatch(styles, /\.composer-box:focus-within\s*\{[^}]*var\(--focus-ring\)/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*min-height:\s*56px/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*max-height:\s*180px/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.composer-box textarea:focus-visible\s*\{[^}]*box-shadow:\s*none/);
  assert.match(styles, /\.composer-box textarea:focus-visible\s*\{[^}]*outline:\s*0/);
  assert.match(styles, /\.send-button\s*\{[^}]*width:\s*30px/);
  assert.match(styles, /\.send-button\s*\{[^}]*height:\s*30px/);
  assert.match(styles, /\.send-button\s*\{[^}]*position:\s*relative/);
  assert.match(styles, /\.send-button\s*\{[^}]*flex:\s*0 0 30px/);
  assert.match(styles, /\.send-button\s*\{[^}]*appearance:\s*none/);
  assert.match(styles, /\.send-button\s*\{[^}]*border-radius:\s*999px/);
  assert.match(styles, /\.send-button\s*\{[^}]*line-height:\s*0/);
  assert.match(styles, /\.send-button\s*\{[^}]*padding:\s*0/);
  assert.doesNotMatch(styles, /\.send-button:hover:not\(:disabled\),[\s\S]*\.send-button:focus-visible\s*\{[^}]*translateY/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*position:\s*absolute/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*top:\s*50%/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*left:\s*50%/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*transform:\s*translate\(-50%,\s*-50%\)/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*display:\s*block/);
  assert.match(styles, /\.send-button svg,[\s\S]*\.stop-icon\s*\{[^}]*margin:\s*0/);
  assert.match(composer, /className="stop-icon"/);
  assert.match(composer, /data-tooltip="Остановить"/);
  assert.match(composer, /data-tooltip="Отправить"/);
  assert.match(composer, /data-tooltip-align="end"/);
  assert.match(styles, /\.stop-icon\s*\{[^}]*width:\s*9px/);
  assert.match(styles, /\.stop-icon\s*\{[^}]*height:\s*9px/);
  assert.match(styles, /\.stop-icon\s*\{[^}]*background:\s*currentColor/);
  assert.match(composer, /COMPOSER_TEXTAREA_MIN_HEIGHT = 56/);
  assert.match(composer, /COMPOSER_TEXTAREA_MAX_HEIGHT = 180/);
  assert.match(composer, /textarea\.scrollHeight/);
  assert.match(composer, /textarea\.style\.height/);
  assert.match(composer, /className="composer-surface"/);
});

test("context budget is rendered inside the chat composer", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const meter = readFileSync(join(srcRoot, "components", "chat", "ComposerContextMeter.tsx"), "utf8");
  const contextWindow = readFileSync(join(srcRoot, "runtime", "contextWindow.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.doesNotMatch(app, /ContextPanel/);
  assert.match(composer, /ComposerContextMeter/);
  assert.match(composer, /className="composer-footer"/);
  assert.match(meter, /composer-context-icon/);
  assert.match(meter, /composer-context-popover/);
  assert.match(meter, /buildContextWindowView/);
  assert.match(meter, /formatContextTokenCount/);
  assert.doesNotMatch(meter, /CONTEXT_MAX_TOKENS/);
  assert.match(contextWindow, /used_tokens/);
  assert.match(contextWindow, /max_tokens/);
  assert.match(contextWindow, /remaining_tokens/);
  assert.match(contextWindow, /}к`/);
  assert.doesNotMatch(styles, /34,\s*197,\s*94|#86efac|#b7f7cb/i);
  assert.match(styles, /stroke: var\(--primary\)/);
  assert.match(styles, /\.composer-context-popover\s*\{[^}]*left:\s*50%/);
  assert.match(styles, /\.composer-context-popover\s*\{[^}]*transform:\s*translateX\(-50%\)/);
});

test("composer context button opens a detailed context window overlay", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const meter = readFileSync(join(srcRoot, "components", "chat", "ComposerContextMeter.tsx"), "utf8");
  const overlay = readFileSync(join(srcRoot, "components", "context", "ContextWindowOverlay.tsx"), "utf8");
  const contextWindow = readFileSync(join(srcRoot, "runtime", "contextWindow.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /ContextWindowOverlay/);
  assert.match(app, /contextWindowOpen/);
  assert.match(app, /effectiveModelName/);
  assert.match(app, /const modelName = effectiveModelName\(runtimeStatus\?\.config\)/);
  assert.match(app, /modelName=\{modelName\}/);
  assert.match(app, /onOpenContextWindow=\{\(\) => setContextWindowOpen\(true\)\}/);
  assert.match(composer, /onOpenContextWindow\?: \(\) => void/);
  assert.match(composer, /ComposerContextMeter[\s\S]*onOpenContextWindow=\{onOpenContextWindow\}/);
  assert.match(meter, /onOpenContextWindow/);
  assert.match(meter, /type="button"/);
  assert.match(meter, /onClick=\{onOpenContextWindow\}/);
  assert.match(overlay, /RuntimeContextState/);
  assert.match(overlay, /modelName: string/);
  assert.match(overlay, /buildContextWindowView/);
  assert.match(overlay, /formatContextBudgetLine/);
  assert.match(overlay, /formatContextBudgetLine\(budget, modelName\)/);
  assert.match(overlay, /contextRecordPreview/);
  assert.match(overlay, /isExpandableContextRecord/);
  assert.match(overlay, /useState<Set<string>>/);
  assert.match(overlay, /context-window-budget-line/);
  assert.doesNotMatch(overlay, /Текущее состояние контекста/);
  assert.match(overlay, /Развернуть/);
  assert.match(overlay, /Свернуть/);
  assert.match(overlay, /aria-expanded=\{expanded\}/);
  assert.doesNotMatch(overlay, /function ContextStat|<ContextStat/);
  assert.match(contextWindow, /RuntimeContextState/);
  assert.match(contextWindow, /formatContextBudgetLine\(budget: ContextBudgetView, modelName = "unknown"\)/);
  assert.match(contextWindow, /`Контекст \$\{modelName\}: /);
  assert.doesNotMatch(contextWindow, /Контекст модели/);
  assert.match(overlay, /role="dialog"/);
  assert.match(overlay, /context-window-overlay/);
  assert.match(contextWindow, /context\.fragments/);
  assert.match(contextWindow, /context\.references/);
  assert.match(contextWindow, /context\.attachments/);
  assert.match(contextWindow, /context\.errors/);
  assert.match(contextWindow, /context\.budget/);
  assert.doesNotMatch(overlay, /fetch\(|requestJson|\/sessions|apiUrl\("\/context|requestJson<.*>\("\/context/);
  assert.match(styles, /\.context-window-overlay\s*\{[^}]*position:\s*fixed/);
  assert.match(styles, /\.context-window-overlay\s*\{[^}]*padding:\s*0/);
  assert.match(styles, /\.context-window-overlay\s*\{[^}]*backdrop-filter:\s*blur/);
  assert.match(styles, /\.context-window-page\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.context-window-page\s*\{[^}]*height:\s*100%/);
  assert.doesNotMatch(styles, /\.context-window-page\s*\{[^}]*max-height:\s*min/);
  assert.match(styles, /\.context-window-progress span\s*\{[^}]*background:\s*var\(--success\)/);
  assert.match(styles, /\.context-window-expand-button/);
  assert.match(styles, /\.context-window-fragment/);
});

test("composer action menu opens from a left aligned plus button", () => {
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const actionMenu = readFileSync(join(srcRoot, "components", "chat", "ComposerActionMenu.tsx"), "utf8");
  const icons = readFileSync(join(srcRoot, "icons.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(composer, /ComposerActionMenu/);
  assert.match(composer, /className="composer-footer-left"[\s\S]*<ComposerActionMenu/);
  assert.match(composer, /className="composer-footer-right"[\s\S]*ComposerContextMeter[\s\S]*ComposerIntelligencePicker[\s\S]*send-button/);
  assert.match(actionMenu, /IconPlus/);
  assert.match(actionMenu, /IconPaperclip/);
  assert.match(actionMenu, /role="menu"/);
  assert.match(actionMenu, /role="menuitemcheckbox"/);
  assert.match(actionMenu, /aria-checked=\{planningMode\}/);
  assert.match(actionMenu, /Добавить фотографии и файлы/);
  assert.match(actionMenu, /Режим Планирования/);
  assert.match(actionMenu, /Плагины/);
  assert.doesNotMatch(actionMenu, /Включить контекст IDE/);
  assert.match(icons, /IconPaperclip/);
  assert.match(styles, /\.composer-footer\s*\{[^}]*justify-content:\s*space-between/);
  assert.match(styles, /\.composer-footer-left,[\s\S]*\.composer-footer-right\s*\{[^}]*align-items:\s*center/);
  assert.match(styles, /\.composer-action-trigger\s*\{[^}]*width:\s*30px/);
  assert.match(styles, /\.composer-action-popover\s*\{[^}]*left:\s*0/);
  assert.match(styles, /\.composer-action-popover\s*\{[^}]*bottom:\s*calc\(100% \+ 8px\)/);
  assert.match(styles, /\.composer-action-switch-on\s*\{[^}]*background:\s*var\(--primary\)/);
});

test("model intelligence picker sits between context meter and send action", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const chatHook = readFileSync(join(srcRoot, "hooks", "useRuntimeChat.ts"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const picker = readFileSync(join(srcRoot, "components", "chat", "ComposerIntelligencePicker.tsx"), "utf8");
  const model = readFileSync(join(srcRoot, "runtime", "modelIntelligence.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(composer, /ComposerContextMeter[\s\S]*ComposerIntelligencePicker[\s\S]*send-button/);
  assert.match(picker, /Интеллект модели/);
  assert.match(picker, /role="menuitemradio"/);
  assert.match(picker, /Интеллект модели/);
  assert.match(picker, /data-tooltip=\{`Интеллект: \$\{selected\.label\}`\}/);
  assert.match(picker, /data-tooltip-placement="top"/);
  assert.match(picker, /data-tooltip-align="start"/);
  assert.doesNotMatch(picker, /title=/);
  assert.doesNotMatch(picker, /Brain/);
  assert.match(picker, /\{selected\.label\}/);
  assert.doesNotMatch(composer, /useState<ModelIntelligenceLevel>/);
  assert.match(composer, /level: ModelIntelligenceLevel/);
  assert.match(composer, /onIntelligenceChange: \(level: ModelIntelligenceLevel\) => void/);
  assert.match(app, /modelIntelligenceLevel/);
  assert.match(chatHook, /model_intelligence:\s*modelIntelligenceLevel/);
  assert.match(model, /DEFAULT_MODEL_INTELLIGENCE_LEVEL/);
  assert.match(model, /DEFAULT_MODEL_INTELLIGENCE_LEVEL: ModelIntelligenceLevel = "medium"/);
  assert.match(styles, /composer-intelligence-button/);
  assert.match(styles, /composer-intelligence-popover/);
  assert.match(styles, /\.composer-intelligence-popover\s*\{[^}]*left:\s*0/);
  assert.doesNotMatch(styles, /\.composer-(context|intelligence)-popover\s*\{[^}]*box-shadow/);
  assert.doesNotMatch(styles, /34,\s*197,\s*94|#86efac|#b7f7cb/i);
});

test("composer shows typed suggestions for context references and slash commands", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const suggestions = readFileSync(join(srcRoot, "components", "chat", "ComposerSuggestions.tsx"), "utf8");
  const helper = readFileSync(join(srcRoot, "runtime", "composerSuggestions.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /commands=\{commands\}/);
  assert.doesNotMatch(composer, /context-hints/);
  assert.match(composer, /detectComposerSuggestionTrigger/);
  assert.match(composer, /buildCommandSuggestions/);
  assert.match(suggestions, /Команды/);
  assert.match(suggestions, /Контекст/);
  assert.match(helper, /@glob:src\/\*\*\/\*\.py/);
  assert.match(styles, /composer-suggestions/);
  assert.doesNotMatch(styles, /34,\s*197,\s*94|#86efac|#b7f7cb/i);
});

test("settings opens as a separate tabbed page with safe read-only runtime data", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const sidebar = readFileSync(join(srcRoot, "components", "layout", "RuntimeSidebar.tsx"), "utf8");
  const statusApi = readFileSync(join(srcRoot, "api", "status.ts"), "utf8");
  const settingsPage = readFileSync(join(srcRoot, "components", "settings", "SettingsPage.tsx"), "utf8");
  const settingsTabs = readFileSync(join(srcRoot, "components", "settings", "SettingsTabs.tsx"), "utf8");
  const settingsRuntime = readFileSync(join(srcRoot, "runtime", "settingsPage.ts"), "utf8");
  const styles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(app, /type AppView = "chat" \| "settings"/);
  assert.match(app, /activeSettingsTab/);
  assert.match(app, /setAppView\("settings"\)/);
  assert.match(app, /mode=\{appView\}/);
  assert.match(app, /settingsActiveTab=\{activeSettingsTab\}/);
  assert.match(app, /onSettingsTabChange=\{setActiveSettingsTab\}/);
  assert.match(app, /<SettingsPage/);
  assert.match(app, /activeTab=\{activeSettingsTab\}/);
  assert.doesNotMatch(app, /activeDrawer.*settings/);
  assert.match(sidebar, /SettingsTabs/);
  assert.match(sidebar, /mode === "settings"/);
  assert.match(sidebar, /settings-sidebar-heading/);
  assert.doesNotMatch(settingsPage, /SettingsTabs/);
  assert.doesNotMatch(settingsPage, /settings-page-sidebar/);
  assert.match(settingsRuntime, /Общее/);
  assert.match(settingsRuntime, /Внешний вид/);
  assert.match(settingsRuntime, /Конфигурация/);
  assert.match(settingsRuntime, /Серверы MCP/);
  assert.match(settingsRuntime, /Плагины/);
  assert.match(settingsRuntime, /Скилы/);
  assert.match(settingsTabs, /aria-selected/);
  assert.match(settingsPage, /GeneralSettingsTab/);
  assert.match(settingsPage, /AppearanceSettingsTab/);
  assert.match(settingsPage, /ConfigurationSettingsTab/);
  assert.match(settingsPage, /MCPServersSettingsTab/);
  assert.match(statusApi, /\/mcp\/snapshot/);
  assert.doesNotMatch(`${settingsPage}\n${statusApi}`, /plugins\/install|plugins\/update|plugins\/remove|PATCH \/settings|requestJson<.*>\("\/mcp"\)/);
  assert.match(styles, /settings-page-shell/);
  assert.match(styles, /\.settings-page-shell\s*\{[^}]*width:\s*min\(760px,\s*100%\)/);
  assert.match(styles, /\.settings-page-shell\s*\{[^}]*margin:\s*96px auto 0/);
  assert.match(styles, /settings-tab-active/);
});

test("MCP settings tab presents list and read-only server editor screens", () => {
  const mcpTab = readFileSync(join(srcRoot, "components", "settings", "MCPServersSettingsTab.tsx"), "utf8");
  const mcpRuntime = readFileSync(join(srcRoot, "runtime", "mcpSettings.ts"), "utf8");
  const settingsPage = readFileSync(join(srcRoot, "components", "settings", "SettingsPage.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(settingsPage, /mcpConfig=\{status\?\.config\?\.values\?\.mcp_config/);
  assert.match(settingsPage, /const showPageHeader = activeTab !== "mcp"/);
  assert.match(mcpTab, /normalizeMCPSettingsSnapshot/);
  assert.match(mcpTab, /mcp-settings-list/);
  assert.match(mcpTab, /mcp-settings-editor/);
  assert.match(mcpTab, /Добавить сервер/);
  assert.match(mcpTab, /Подключиться к пользовательскому MCP/);
  assert.match(mcpRuntime, /Обновление/);
  assert.match(mcpTab, /STDIO/);
  assert.match(mcpTab, /Потоковая передача HTTP/);
  assert.match(mcpTab, /Команда на запуск/);
  assert.match(mcpTab, /Аргументы/);
  assert.match(mcpTab, /Переменные окружения/);
  assert.match(mcpTab, /Рабочая директория/);
  assert.match(mcpTab, /readOnly/);
  assert.match(mcpTab, /disabled/);
  assert.doesNotMatch(mcpTab, /fetch\(|requestJson|PATCH|DELETE|POST|requestJson<.*>\("\/mcp"\)/);
  assert.match(mcpRuntime, /export function normalizeMCPSettingsSnapshot/);
  assert.match(mcpRuntime, /export function mcpServerEditorTitle/);
  assert.match(styles, /\.mcp-settings-list/);
  assert.match(styles, /\.mcp-server-row/);
  assert.match(styles, /\.mcp-transport-tabs/);
  assert.match(styles, /\.mcp-editor-card/);
  assert.match(styles, /\.mcp-editor-actions/);
});

test("settings content is grouped into titled section cards", () => {
  const section = readFileSync(join(srcRoot, "components", "settings", "SettingsSection.tsx"), "utf8");
  const general = readFileSync(join(srcRoot, "components", "settings", "GeneralSettingsTab.tsx"), "utf8");
  const configuration = readFileSync(join(srcRoot, "components", "settings", "ConfigurationSettingsTab.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");

  assert.match(section, /settings-section-group/);
  assert.match(section, /settings-section-card/);
  assert.match(section, /settings-row-main/);
  assert.match(general, /SettingsSection title="Model"/);
  assert.match(general, /SettingsSection title="Safety"/);
  assert.match(configuration, /SettingsSection title="Effective configuration"/);
  assert.match(styles, /\.settings-section-group\s*\{[^}]*gap:\s*14px/);
  assert.match(styles, /\.settings-section-card\s*\{[^}]*border:\s*1px solid var\(--border\)/);
  assert.match(styles, /\.settings-section-card\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.settings-row\s*\{[^}]*border-bottom:\s*1px solid var\(--border\)/);
  assert.match(styles, /\.settings-row-main\s*\{[^}]*display:\s*grid/);
});

test("settings preference dropdowns use app-styled popovers instead of native selects", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const appearance = readFileSync(join(srcRoot, "components", "settings", "AppearanceSettingsTab.tsx"), "utf8");
  const settingsPage = readFileSync(join(srcRoot, "components", "settings", "SettingsPage.tsx"), "utf8");
  const themeAppearance = readFileSync(join(srcRoot, "components", "settings", "ThemeAppearanceSection.tsx"), "utf8");
  const uiPreferences = readFileSync(join(srcRoot, "components", "settings", "UIPreferencesSection.tsx"), "utf8");
  const settingsRuntime = readFileSync(join(srcRoot, "runtime", "settingsPage.ts"), "utf8");
  const runtimePreferences = readFileSync(join(srcRoot, "runtime", "uiPreferences.ts"), "utf8");
  const settingsSelect = readFileSync(join(srcRoot, "components", "settings", "SettingsSelect.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "components", "settings", "settings.css"), "utf8");
  const appStyles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /themeCSSVariables\(preferences\)/);
  assert.match(app, /style=\{shellStyle\}/);
  assert.match(appearance, /ThemeAppearanceSection/);
  assert.match(themeAppearance, /theme-mode-toggle/);
  assert.match(themeAppearance, /type="color"/);
  assert.match(themeAppearance, /type="range"/);
  assert.match(themeAppearance, /updateThemeConfig/);
  assert.match(themeAppearance, /Скопировать тему/);
  assert.match(runtimePreferences, /export function updateThemeConfig/);
  assert.match(runtimePreferences, /export function themeCSSVariables/);
  assert.match(runtimePreferences, /--font-size-caption/);
  assert.match(runtimePreferences, /--font-size-heading/);
  assert.match(runtimePreferences, /--font-size-code/);
  assert.match(runtimePreferences, /--app-interactive-cursor/);
  assert.match(runtimePreferences, /blockRadius/);
  assert.match(runtimePreferences, /--ui-element-radius/);
  assert.match(themeAppearance, /codeFontSize[\s\S]*Радиус блоков[\s\S]*blockRadius/);
  assert.match(uiPreferences, /SettingsSelect/);
  assert.doesNotMatch(uiPreferences, /blockRadius/);
  assert.doesNotMatch(uiPreferences, /<select|<option/);
  assert.match(settingsSelect, /role="listbox"/);
  assert.match(settingsSelect, /role="option"/);
  assert.match(settingsSelect, /aria-selected/);
  assert.match(settingsSelect, /IconChevronDown/);
  assert.match(settingsSelect, /IconCheck/);
  assert.match(styles, /\.settings-select-popover\s*\{[^}]*background:\s*var\(--card-elevated\)/);
  assert.match(styles, /\.settings-select-popover\s*\{[^}]*border:\s*1px solid var\(--border\)/);
  assert.match(styles, /\.settings-select-popover\s*\{[^}]*box-shadow:\s*none/);
  assert.match(styles, /\.settings-select-option-selected/);
  assert.match(styles, /\.theme-preview\s*\{[^}]*display:\s*grid/);
  assert.match(styles, /\.theme-mode-button-active/);
  assert.match(styles, /\.settings-switch-on\s*\{[^}]*background:\s*var\(--primary\)/);
  assert.match(appStyles, /button\s*\{[^}]*cursor:\s*var\(--app-interactive-cursor\)/);
  assert.match(appStyles, /body\s*\{[^}]*font-size:\s*var\(--font-size-body\)/);
  assert.match(appStyles, /code,[\s\S]*pre\s*\{[^}]*font-size:\s*var\(--font-size-code\)/);
  assert.match(appStyles, /font-size:\s*var\(--font-size-small\)/);
  assert.match(appStyles, /font-size:\s*var\(--font-size-caption\)/);
  assert.match(styles, /font-size:\s*var\(--font-size-heading\)/);
  assert.match(appStyles, /\.app-shell\s*\{[^}]*color:\s*var\(--foreground\)/);
  assert.match(appStyles, /\.app-shell\s*\{[^}]*font-family:\s*var\(--font-sans\)/);
  assert.doesNotMatch(
    `${settingsPage}\n${settingsRuntime}\n${themeAppearance}\n${uiPreferences}`,
    new RegExp(
      [
        "Local interface " + "preferences",
        "Backend\\/runtime " + "settings",
        "local " + "only",
        "These preferences are " + "stored",
        "frontend " + "only",
      ].join("|"),
    ),
  );
});
