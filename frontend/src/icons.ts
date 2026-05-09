import { createElement, type SVGProps } from "react";

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
  width?: number;
  x?: number;
  x1?: number;
  x2?: number;
  y?: number;
  y1?: number;
  y2?: number;
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

export const IconArrowUp = makeIcon([{ d: "M12 19V5" }, { d: "M5 12l7-7 7 7" }]);
export const IconAt = makeIcon([
  { cx: 12, cy: 12, r: 4 },
  { d: "M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" },
]);
export const IconBlocks = makeIcon([
  { x: 4, y: 4, width: 6, height: 6, rx: 1 },
  { x: 14, y: 4, width: 6, height: 6, rx: 1 },
  { x: 4, y: 14, width: 6, height: 6, rx: 1 },
  { x: 14, y: 14, width: 6, height: 6, rx: 1 },
]);
export const IconCheck = makeIcon([{ d: "M5 12l5 5L20 7" }]);
export const IconChevronDown = makeIcon([{ d: "M6 9l6 6 6-6" }]);
export const IconChevronRight = makeIcon([{ d: "M9 6l6 6-6 6" }]);
export const IconCommand = makeIcon([
  { d: "M9 9h6v6H9z" },
  { d: "M5 9a2 2 0 1 1 4 0v2H7a2 2 0 0 1-2-2" },
  { d: "M19 9a2 2 0 1 0-4 0v2h2a2 2 0 0 0 2-2" },
  { d: "M5 15a2 2 0 1 0 4 0v-2H7a2 2 0 0 0-2 2" },
  { d: "M19 15a2 2 0 1 1-4 0v-2h2a2 2 0 0 1 2 2" },
]);
export const IconCopy = makeIcon([
  { x: 8, y: 8, width: 11, height: 11, rx: 2 },
  { d: "M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" },
]);
export const IconDownload = makeIcon([{ d: "M12 3v12" }, { d: "M7 10l5 5 5-5" }, { d: "M5 21h14" }]);
export const IconFileText = makeIcon([
  { d: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" },
  { d: "M14 3v5h5" },
  { d: "M9 13h6" },
  { d: "M9 17h4" },
]);
export const IconGitCompare = makeIcon([
  { cx: 7, cy: 5, r: 2 },
  { cx: 17, cy: 19, r: 2 },
  { d: "M7 7v10a2 2 0 0 0 2 2h6" },
  { d: "M17 17V7a2 2 0 0 0-2-2H9" },
]);
export const IconHelpCircle = makeIcon([
  { cx: 12, cy: 12, r: 9 },
  { d: "M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4" },
  { d: "M12 17h.01" },
]);
export const IconLayoutSidebarLeftExpand = makeIcon([
  { x: 4, y: 4, width: 16, height: 16, rx: 2 },
  { d: "M9 4v16" },
  { d: "M14 10l2 2-2 2" },
]);
export const IconListCheck = makeIcon([{ d: "M10 6h10" }, { d: "M10 12h10" }, { d: "M10 18h10" }, { d: "M4 6l1.5 1.5L8 5" }, { d: "M4 12l1.5 1.5L8 11" }, { d: "M4 18l1.5 1.5L8 17" }]);
export const IconMessages = makeIcon([
  { d: "M7 8h10" },
  { d: "M7 12h6" },
  { d: "M5 4h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-8l-5 4v-4H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" },
]);
export const IconPlus = makeIcon([{ d: "M12 5v14" }, { d: "M5 12h14" }]);
export const IconSearch = makeIcon([{ cx: 10, cy: 10, r: 6 }, { d: "M15 15l5 5" }]);
export const IconSettings = makeIcon([
  { cx: 12, cy: 12, r: 3 },
  { d: "M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2 3-.2-.1a1.7 1.7 0 0 0-2 .1 1.7 1.7 0 0 0-.8 1.7V22h-3.6v-.3a1.7 1.7 0 0 0-1.2-1.6 1.7 1.7 0 0 0-1.8.3l-.2.1-2-3 .1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H4v-5h.4a1.7 1.7 0 0 0 1.5-1A1.7 1.7 0 0 0 5.6 6.6l-.1-.1 2-3 .2.1a1.7 1.7 0 0 0 2-.1 1.7 1.7 0 0 0 .8-1.7V2h3.6v.3a1.7 1.7 0 0 0 1.2 1.6 1.7 1.7 0 0 0 1.8-.3l.2-.1 2 3-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.4v5h-.4a1.7 1.7 0 0 0-1.5.5z" },
]);
export const IconShieldExclamation = makeIcon([
  { d: "M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z" },
  { d: "M12 8v5" },
  { d: "M12 17h.01" },
]);
export const IconSparkles = makeIcon([{ d: "M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z" }, { d: "M5 16l.8 2.2L8 19l-2.2.8L5 22l-.8-2.2L2 19l2.2-.8z" }, { d: "M19 13l.8 2.2L22 16l-2.2.8L19 19l-.8-2.2L16 16l2.2-.8z" }]);
export const IconX = makeIcon([{ d: "M18 6L6 18" }, { d: "M6 6l12 12" }]);
