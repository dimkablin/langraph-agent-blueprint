import { IconBlocks, IconGitCompare, IconListCheck } from "../../icons.ts";

export type WelcomePromptExample = {
  title: string;
  prompt: string;
  icon: "review" | "plugin" | "plan";
};

const EXAMPLE_ICONS = {
  review: IconGitCompare,
  plugin: IconBlocks,
  plan: IconListCheck,
} satisfies Record<WelcomePromptExample["icon"], typeof IconGitCompare>;

export function WelcomePromptExamples({
  disabled,
  examples,
  onSelect,
}: {
  disabled?: boolean;
  examples: WelcomePromptExample[];
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="welcome-examples" aria-label="Примеры задач">
      {examples.map((example) => {
        const Icon = EXAMPLE_ICONS[example.icon];
        return (
          <button
            key={example.title}
            className="welcome-example"
            type="button"
            disabled={disabled}
            onClick={() => onSelect(example.prompt)}
          >
            <Icon size={17} />
            <span>{example.title}</span>
          </button>
        );
      })}
    </div>
  );
}
