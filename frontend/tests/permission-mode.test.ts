import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import test from "node:test";

import {
  DEFAULT_PERMISSION_MODE,
  FULL_ACCESS_PERMISSION_MODE,
  loadPermissionMode,
  PERMISSION_MODE_OPTIONS,
  PERMISSION_MODE_STORAGE_KEY,
  permissionModeOptionById,
  savePermissionMode,
} from "../src/runtime/permissionMode.ts";

class MemoryStorage {
  values = new Map<string, string>();

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }
}

test("permission mode options expose the required Russian labels and backend mode ids", () => {
  assert.deepEqual(
    PERMISSION_MODE_OPTIONS.map((option) => [option.label, option.id]),
    [
      ["Разрешение по умолчанию", "default"],
      ["Полный доступ", "bypass_read_only"],
    ],
  );
  assert.equal(DEFAULT_PERMISSION_MODE, "default");
  assert.equal(FULL_ACCESS_PERMISSION_MODE, "bypass_read_only");
  assert.equal(permissionModeOptionById("default").label, "Разрешение по умолчанию");
  assert.equal(permissionModeOptionById("bypass_read_only").risk, "elevated");
  assert.ok(PERMISSION_MODE_OPTIONS.every((option) => !("description" in option)));
});

test("permission mode picker renders only icons, labels, and selected checkmark", () => {
  const srcRoot = join(import.meta.dirname, "..", "src");
  const picker = readFileSync(join(srcRoot, "components", "chat", "ComposerPermissionModePicker.tsx"), "utf8");
  const styles = readFileSync(join(srcRoot, "styles.css"), "utf8");

  assert.doesNotMatch(picker, /permission-mode-option-description|permission-mode-warning|option\.description/);
  assert.doesNotMatch(picker, /Агент запрашивает подтверждение|Расширяет доступ инструментов|Полный доступ не включается по умолчанию/);
  assert.match(picker, /<SelectedModeIcon size=\{14\} \/>\s*<span>\{selected\.label\}<\/span>/);
  assert.match(picker, /<PermissionModeIcon size=\{14\} \/>\s*\{option\.label\}/);
  assert.match(picker, /\{isSelected \? <IconCheck size=\{16\} \/> : null\}/);
  const permissionStyles = styles.slice(styles.indexOf(".composer-permission-control"), styles.indexOf(".send-button"));

  assert.doesNotMatch(picker, /permission-mode-option-selected|composer-permission-button-elevated/);
  assert.doesNotMatch(permissionStyles, /permission-mode-option-selected|composer-permission-button-elevated|\[aria-expanded="true"\]/);
});

test("permission mode preference persists non-default selection and defaults safely", () => {
  const storage = new MemoryStorage();

  assert.equal(loadPermissionMode(storage), "default");
  savePermissionMode("bypass_read_only", storage);
  assert.equal(storage.getItem(PERMISSION_MODE_STORAGE_KEY), "bypass_read_only");
  assert.equal(loadPermissionMode(storage), "bypass_read_only");

  savePermissionMode("default", storage);
  assert.equal(storage.getItem(PERMISSION_MODE_STORAGE_KEY), null);
  storage.setItem(PERMISSION_MODE_STORAGE_KEY, "strict");
  assert.equal(loadPermissionMode(storage), "default");
});

test("composer wires permission mode picker into stream request state", () => {
  const srcRoot = join(import.meta.dirname, "..", "src");
  const composer = readFileSync(join(srcRoot, "components", "chat", "ChatComposer.tsx"), "utf8");
  const hook = readFileSync(join(srcRoot, "hooks", "useRuntimeChat.ts"), "utf8");
  const schemas = readFileSync(join(srcRoot, "api", "schemas.ts"), "utf8");

  assert.match(composer, /<ComposerActionMenu \/>\s*<ComposerPermissionModePicker/);
  assert.match(composer, /permissionMode: PermissionMode/);
  assert.match(hook, /permission_mode: permissionMode/);
  assert.match(hook, /savePermissionMode\(permissionMode\)/);
  assert.match(schemas, /permission_mode\?: PermissionMode \| null/);
});
