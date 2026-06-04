import { createElement, type SVGProps } from "react";

// Glyph paths mirror lucide-react v0.487.0 from the donor widget project.
// They stay local so the frontend keeps a single lightweight icon boundary.
export type AppIconProps = Omit<SVGProps<SVGSVGElement>, "height" | "width"> & {
  size?: number | string;
};

type IconPath = {
  d?: string;
  cx?: number;
  cy?: number;
  fill?: string;
  height?: number;
  r?: number;
  rx?: number;
  ry?: number;
  width?: number;
  x?: number;
  y?: number;
};

function makeIcon(paths: IconPath[]) {
  return function AppIcon({ size = 24, strokeWidth = 2, ...props }: AppIconProps) {
    return createElement(
      "svg",
      {
        "aria-hidden": props["aria-label"] ? undefined : true,
        fill: "none",
        height: size,
        stroke: "currentColor",
        strokeLinecap: "round",
        strokeLinejoin: "round",
        strokeWidth,
        vectorEffect: "non-scaling-stroke",
        viewBox: "0 0 24 24",
        width: size,
        ...props,
      },
      paths.map((path, index) => {
        const key = `${path.d ?? `${path.x}-${path.y}`}-${index}`;
        if (path.d) return createElement("path", { key, ...path });
        if (path.cx != null && path.cy != null && path.r != null) return createElement("circle", { key, ...path });
        return createElement("rect", { key, ...path });
      }),
    );
  };
}

export const IconArrowUp = makeIcon([
  { d: "M12 19V5" },
  { d: "m5 12 7-7 7 7" },
]);
export const IconArrowLeft = makeIcon([{ d: "m12 19-7-7 7-7" }, { d: "M19 12H5" }]);
export const IconAt = makeIcon([
  { cx: 12, cy: 12, r: 4 },
  { d: "M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" },
]);
export const IconBlocks = makeIcon([
  { x: 14, y: 3, width: 7, height: 7, rx: 1 },
  { d: "M10 21V8a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5a1 1 0 0 0-1-1H3" },
]);
export const IconMoreHorizontal = makeIcon([
  { cx: 12, cy: 12, r: 1 },
  { cx: 19, cy: 12, r: 1 },
  { cx: 5, cy: 12, r: 1 },
]);
export const IconCheck = makeIcon([{ d: "M20 6 9 17l-5-5" }]);
export const IconChevronDown = makeIcon([{ d: "m6 9 6 6 6-6" }]);
export const IconChevronRight = makeIcon([{ d: "m9 18 6-6-6-6" }]);
export const IconCommand = makeIcon([{ d: "M15 6v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3" }]);
export const IconCopy = makeIcon([
  { x: 8, y: 8, width: 14, height: 14, rx: 2, ry: 2 },
  { d: "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" },
]);
export const IconDownload = makeIcon([
  { d: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" },
  { d: "m7 10 5 5 5-5" },
  { d: "M12 15V3" },
]);
export const IconFileText = makeIcon([
  { d: "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" },
  { d: "M14 2v4a2 2 0 0 0 2 2h4" },
  { d: "M10 9H8" },
  { d: "M16 13H8" },
  { d: "M16 17H8" },
]);
export const IconFolder = makeIcon([
  { d: "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9l-.81-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" },
]);
export const IconGitCompare = makeIcon([
  { cx: 18, cy: 18, r: 3 },
  { cx: 6, cy: 6, r: 3 },
  { d: "M13 6h3a2 2 0 0 1 2 2v7" },
  { d: "M11 18H8a2 2 0 0 1-2-2V9" },
]);
export const IconHelpCircle = makeIcon([
  { cx: 12, cy: 12, r: 10 },
  { d: "M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" },
  { d: "M12 17h.01" },
]);
export const IconLayoutSidebarLeftExpand = makeIcon([
  { x: 3, y: 3, width: 18, height: 18, rx: 2 },
  { d: "M9 3v18" },
  { d: "m14 9 3 3-3 3" },
]);
export const IconListCheck = makeIcon([
  { d: "m3 17 2 2 4-4" },
  { d: "m3 7 2 2 4-4" },
  { d: "M13 6h8" },
  { d: "M13 12h8" },
  { d: "M13 18h8" },
]);
export const IconMessages = makeIcon([{ d: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" }]);
export const IconPaperclip = makeIcon([
  { d: "m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" },
]);
export const IconPlus = makeIcon([{ d: "M5 12h14" }, { d: "M12 5v14" }]);
export const IconSearch = makeIcon([{ cx: 11, cy: 11, r: 8 }, { d: "m21 21-4.3-4.3" }]);
export const IconSettings = makeIcon([
  { d: "M20 7h-9" },
  { d: "M14 17H5" },
  { cx: 17, cy: 17, r: 3 },
  { cx: 7, cy: 7, r: 3 },
]);
export const IconShield = makeIcon([
  { d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" },
]);
export const IconTrash = makeIcon([
  { d: "M3 6h18" },
  { d: "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" },
  { d: "M19 6 18 20a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" },
  { d: "M10 11v6" },
  { d: "M14 11v6" },
]);
export const IconMoon = makeIcon([{ d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" }]);
export const IconMonitor = makeIcon([
  { x: 2, y: 3, width: 20, height: 14, rx: 2 },
  { d: "M8 21h8" },
  { d: "M12 17v4" },
]);
export const IconSun = makeIcon([
  { cx: 12, cy: 12, r: 4 },
  { d: "M12 2v2" },
  { d: "M12 20v2" },
  { d: "m4.93 4.93 1.41 1.41" },
  { d: "m17.66 17.66 1.41 1.41" },
  { d: "M2 12h2" },
  { d: "M20 12h2" },
  { d: "m6.34 17.66-1.41 1.41" },
  { d: "m19.07 4.93-1.41 1.41" },
]);
export const IconType = makeIcon([
  { d: "M4 7V4h16v3" },
  { d: "M9 20h6" },
  { d: "M12 4v16" },
]);
export const IconShieldExclamation = makeIcon([
  { d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" },
  { d: "M12 8v4" },
  { d: "M12 16h.01" },
]);
export const IconSparkles = makeIcon([
  { d: "M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" },
  { d: "M20 3v4" },
  { d: "M22 5h-4" },
  { d: "M4 17v2" },
  { d: "M5 18H3" },
]);
export const IconX = makeIcon([{ d: "M18 6 6 18" }, { d: "m6 6 12 12" }]);
