"use client";

export interface Tab {
  id: string;
  label: string;
}

export interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

function Tabs({ tabs, activeTab, onChange, className = "" }: TabsProps) {
  if (tabs.length === 0) return null;

  return (
    <div
      className={[
        "flex border-b border-[#1e1e3a] overflow-x-auto",
        className,
      ].join(" ")}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={[
              "relative px-4 py-2.5 text-sm font-medium whitespace-nowrap transition-colors duration-150",
              "focus-visible:outline-none focus-visible:bg-[#1e1e3a]/50",
              "cursor-pointer select-none",
              isActive
                ? "text-white"
                : "text-[#666688] hover:text-[#a0a0c0]",
            ].join(" ")}
          >
            {tab.label}
            {/* Active indicator bar */}
            {isActive && (
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#00d4aa] rounded-full"
                aria-hidden="true"
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

export { Tabs };
