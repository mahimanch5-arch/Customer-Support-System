/** Inline stroke icons — no icon library, so nothing to load. */
const base = {
  width: 18,
  height: 18,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
};

export const PlusIcon = () => (
  <svg {...base}><path d="M12 5v14M5 12h14" /></svg>
);

export const SendIcon = () => (
  <svg {...base}><path d="M12 19V5M5 12l7-7 7 7" /></svg>
);

export const StopIcon = () => (
  <svg {...base}><rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" stroke="none" /></svg>
);

export const TrashIcon = () => (
  <svg {...base} width={16} height={16}>
    <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
  </svg>
);

export const SidebarIcon = () => (
  <svg {...base}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></svg>
);

export const RetryIcon = () => (
  <svg {...base} width={15} height={15}>
    <path d="M20 12a8 8 0 1 1-3-6.2M20 4v5h-5" />
  </svg>
);

export const SparkIcon = () => (
  <svg {...base} width={16} height={16}>
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z" />
  </svg>
);
