import type { Turn } from '../types';
import { MessageBubble } from './MessageBubble';
import { RetryIcon } from './Icons';

interface Props {
  turn: Turn;
  /** The last turn, while a stream is live. */
  isStreaming: boolean;
  onRetry: (turnId: string) => void;
}

/** A turn = one human message + one AI response. */
export function TurnView({ turn, isStreaming, onRetry }: Props) {
  const waiting = turn.status === 'pending' && !turn.ai;

  return (
    <article className="turn" data-turn-id={turn.id}>
      <MessageBubble message={turn.human} />

      {turn.ai && <MessageBubble message={turn.ai} />}

      {waiting && (
        <div className="msg msg--ai">
          <div className="msg__role">Support Assistant</div>
          <div className="typing" aria-label="Assistant is typing">
            <span /><span /><span />
          </div>
        </div>
      )}

      {isStreaming && turn.ai && <div className="caret" aria-hidden="true" />}

      {turn.status === 'error' && (
        <div className="turn__error" role="status">
          <span>{turn.error ?? 'Something went wrong.'}</span>
          <button type="button" onClick={() => onRetry(turn.id)}>
            <RetryIcon />
            Retry
          </button>
        </div>
      )}
    </article>
  );
}
