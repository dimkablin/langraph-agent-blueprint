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
  assert.doesNotMatch(text, /lucide-react/);
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
  const bubble = readFileSync(join(srcRoot, "components", "chat", "MessageBubble.tsx"), "utf8");

  assert.doesNotMatch(app, /activeDrawer === "chats"/);
  assert.doesNotMatch(app, /title="Чаты"/);
  assert.match(app, /title="Commands \/ Skills \/ Tools"/);
  assert.match(app, /title="Настройки"/);
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

test("header action buttons are borderless icon-only controls", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /\.app-header\s*\{[^}]*border-bottom:\s*0/);
  assert.match(styles, /\.app-header\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.app-header\s*\{[^}]*justify-content:\s*space-between/);
  assert.match(styles, /\.header-leading\s*\{[^}]*display:\s*flex/);
  assert.match(styles, /\.icon-button\s*\{[^}]*border:\s*0/);
  assert.match(styles, /\.icon-button\s*\{[^}]*background:\s*transparent/);
  assert.match(styles, /\.icon-button\s*\{[^}]*padding:\s*0/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*content:\s*attr\(data-tooltip\)/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*background:\s*var\(--card-elevated\)/);
  assert.match(styles, /\[data-tooltip\]::after\s*\{[^}]*max-width:\s*min\(220px,\s*calc\(100vw - 24px\)\)/);
  assert.match(styles, /\[data-tooltip\]\[data-tooltip-align="start"\]::after/);
  assert.match(styles, /\[data-tooltip\]\[data-tooltip-align="end"\]::after/);
  assert.match(styles, /\[data-tooltip\]:hover::after/);
  assert.match(styles, /\.icon-button:hover,[\s\S]*\.icon-button:focus-visible\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.08\)/);
  assert.doesNotMatch(styles, /\.icon-button\s*\{[^}]*border:\s*1px/);
  assert.doesNotMatch(styles, /brand-lockup|brand-mark/);
});

test("scrollbars are thin and match the chat background", () => {
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /--scrollbar-track:\s*var\(--background\)/);
  assert.match(styles, /scrollbar-width:\s*thin/);
  assert.match(styles, /\*::-webkit-scrollbar\s*\{[^}]*width:\s*6px/);
  assert.match(styles, /\*::-webkit-scrollbar\s*\{[^}]*height:\s*6px/);
  assert.match(styles, /\*::-webkit-scrollbar-track\s*\{[^}]*background:\s*var\(--scrollbar-track\)/);
});

test("message metadata renders outside the message block and appears on hover", () => {
  const bubble = readFileSync(join(srcRoot, "components", "chat", "MessageBubble.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(bubble, /MessageMeta/);
  assert.match(bubble, /Copy message/);
  assert.match(bubble, /navigator\.clipboard\.writeText/);
  assert.match(bubble, /<div className=\{isUser \? "message-card message-card-user" : "message-card"\}>[\s\S]*<\/div>\s*<MessageMeta/);
  assert.doesNotMatch(styles, /\.message-card time/);
  assert.match(styles, /\.message-meta\s*\{[^}]*opacity:\s*0/);
  assert.match(styles, /\.message-meta\s*\{[^}]*pointer-events:\s*none/);
  assert.match(styles, /\.message-row:hover \.message-meta/);
  assert.match(styles, /\.message-copy-button/);
});

test("main page keeps only chat while registries live behind the help drawer", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.doesNotMatch(app, /EventTimeline/);
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
  assert.match(styles, /\.welcome-examples\s*\{[^}]*margin-top:\s*28px/);
  assert.match(styles, /\.welcome-examples\s*\{[^}]*padding-inline:\s*18px/);
  assert.match(styles, /\.welcome-example\s*\{[^}]*border-top:\s*1px solid/);
  assert.match(styles, /\.welcome-example:first-child\s*\{[^}]*border-top:\s*0/);
  assert.match(styles, /\.welcome-example:hover,[\s\S]*\.welcome-example:focus-visible\s*\{[^}]*background:\s*transparent/);
});

test("runtime sidebar is a persistent layout block toggled by the header button", () => {
  const app = readFileSync(join(srcRoot, "App.tsx"), "utf8");
  const header = readFileSync(join(srcRoot, "components", "layout", "StatusHeader.tsx"), "utf8");
  const sidebar = readFileSync(join(srcRoot, "components", "layout", "RuntimeSidebar.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(app, /sidebarOpen/);
  assert.match(app, /app-shell app-shell-sidebar-open/);
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
  assert.doesNotMatch(styles, /\.runtime-sidebar\s*\{[^}]*position:\s*fixed/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*flex:\s*0 0 280px/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*height:\s*100vh/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*overflow:\s*hidden/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.runtime-sidebar\s*\{[^}]*padding:\s*0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*width:\s*calc\(100% - 8px\)/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*height:\s*100%/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*min-height:\s*0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*border-radius:\s*0 var\(--control-radius\) var\(--control-radius\) 0/);
  assert.match(styles, /\.runtime-sidebar-panel\s*\{[^}]*margin-right:\s*8px/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*flex:\s*1/);
  assert.match(styles, /\.runtime-sidebar-chat-list\s*\{[^}]*overflow:\s*auto/);
  assert.match(styles, /\.runtime-sidebar-bottom\s*\{[^}]*margin-top:\s*auto/);
});

test("chat presentation borrows widget width, message blocks, and floating composer", () => {
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.match(styles, /--surface-radius:\s*18px/);
  assert.match(styles, /--control-radius:\s*11px/);
  assert.match(styles, /--radius:\s*var\(--control-radius\)/);
  assert.match(styles, /--chat-block-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /--chat-column-width:\s*760px/);
  assert.match(styles, /--chat-edge-gap:\s*12px/);
  assert.match(styles, /\.icon-button\s*\{[^}]*border-radius:\s*var\(--control-radius\)/);
  assert.match(styles, /\.chat-column\s*\{[^}]*flex:\s*0 1 auto/);
  assert.match(styles, /\.chat-column\s*\{[^}]*width:\s*min\(var\(--chat-column-width\),\s*calc\(100% - 24px\)\)/);
  assert.match(styles, /\.chat-column\s*\{[^}]*max-width:\s*var\(--chat-column-width\)/);
  assert.match(styles, /\.chat-scroll\s*\{[^}]*padding:\s*22px 0 150px/);
  assert.match(styles, /\.message-row\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.message-card\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*max-width:\s*min\(720px,\s*88%\)/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.message-card-user\s*\{[^}]*background:\s*color-mix\(in oklab,\s*var\(--card-elevated\)/);
  assert.doesNotMatch(styles, /\.message-card-user\s*\{[^}]*background:\s*var\(--primary\)/);
  assert.match(styles, /\.composer\s*\{[^}]*position:\s*sticky/);
  assert.match(styles, /\.composer\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.composer\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.composer\s*\{[^}]*padding:\s*0;/);
  assert.match(styles, /\.composer\s*\{[^}]*margin:\s*-96px 0 0/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*background:\s*var\(--background\)/);
  assert.match(styles, /\.composer-surface\s*\{[^}]*border-radius:\s*var\(--surface-radius\) var\(--surface-radius\) 0 0/);
  assert.match(styles, /\.composer-box\s*\{[^}]*width:\s*100%/);
  assert.match(styles, /\.composer-box\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*min-height:\s*56px/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*max-height:\s*180px/);
  assert.match(styles, /\.composer-box textarea\s*\{[^}]*border-radius:\s*var\(--surface-radius\)/);
  assert.match(styles, /\.send-button\s*\{[^}]*width:\s*30px/);
  assert.match(styles, /\.send-button\s*\{[^}]*height:\s*30px/);
  assert.match(styles, /\.send-button\s*\{[^}]*border-radius:\s*999px/);
  assert.match(styles, /\.send-button svg\s*\{[^}]*display:\s*block/);
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
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.doesNotMatch(app, /ContextPanel/);
  assert.match(composer, /ComposerContextMeter/);
  assert.match(composer, /className="composer-footer"/);
  assert.match(meter, /composer-context-icon/);
  assert.match(meter, /composer-context-popover/);
  assert.doesNotMatch(meter, /CONTEXT_MAX_TOKENS/);
  assert.match(meter, /used_tokens/);
  assert.match(meter, /max_tokens/);
  assert.match(meter, /}к`/);
  assert.doesNotMatch(styles, /34,\s*197,\s*94|#86efac|#b7f7cb/i);
  assert.match(styles, /stroke: var\(--primary\)/);
  assert.match(styles, /\.composer-context-popover\s*\{[^}]*left:\s*50%/);
  assert.match(styles, /\.composer-context-popover\s*\{[^}]*transform:\s*translateX\(-50%\)/);
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
