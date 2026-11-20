import { SparkIcon } from './Icons';

const SUGGESTIONS = [
  'Where is my order #A-10428?',
  'I want a refund for the desk lamp',
  'The blanket arrived damaged',
  'My delivery is 4 days late',
];

export function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="empty">
      <div className="empty__mark" aria-hidden="true">
        <SparkIcon />
      </div>
      <h1 className="empty__title">How can I help?</h1>
      <p className="empty__sub">
        Ask about an order, a refund, a return or a delivery. I check your account against
        policy before acting, and I always confirm first.
      </p>

      <ul className="empty__suggestions">
        {SUGGESTIONS.map((s) => (
          <li key={s}>
            <button type="button" onClick={() => onPick(s)}>
              {s}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
