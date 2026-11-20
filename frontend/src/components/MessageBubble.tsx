import type { Message } from '../types';
import { clockTime } from '../lib/format';
import { Markdown } from '../lib/markdown';

/** One human or AI message. Message ID is exposed for later tracing. */
export function MessageBubble({ message }: { message: Message }) {
  const isHuman = message.role === 'human';

  return (
    <div className={`msg msg--${message.role}`} data-message-id={message.id}>
      <div className="msg__role">{isHuman ? 'You' : 'Support Assistant'}</div>

      <div className="msg__body">
        {isHuman ? <p>{message.content}</p> : <Markdown text={message.content} />}
      </div>

      {!isHuman && message.meta && <MetaStrip meta={message.meta} />}

      <div className="msg__foot">
        <time dateTime={message.createdAt}>{clockTime(message.createdAt)}</time>
        <span className="msg__id">{message.id}</span>
      </div>
    </div>
  );
}

function MetaStrip({ meta }: { meta: NonNullable<Message['meta']> }) {
  const { tools = [], citations = [], escalated } = meta;
  if (!tools.length && !citations.length && !escalated) return null;

  return (
    <div className="meta">
      {escalated && <span className="chip chip--warn">Escalated to a human</span>}
      {tools.map((t) => (
        <span className="chip" key={t} title="Tool API the agent called">
          {t}
        </span>
      ))}
      {citations.map((c) => (
        <span className="chip chip--kb" key={c} title="Knowledge base source">
          {c.replace(/^_KB\//, '')}
        </span>
      ))}
    </div>
  );
}
