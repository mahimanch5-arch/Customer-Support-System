import type { Conversation } from '../types';
import { newConversationId, newMessageId, newTurnId } from '../lib/ids';
import { titleFromQuestion } from '../lib/title';
import { replyFor } from './replies';

/** Mock sidebar history, so the app doesn't open empty. */
export function seedConversations(): Conversation[] {
  return [
    build(1, ['Where is my order #A-10428?', 'Is it going to be late?']),
    build(2, ['I want a refund for the desk lamp']),
    build(3, ['The blanket arrived damaged']),
    build(9, ['How much store credit do I have left?']),
  ];
}

function build(daysAgo: number, questions: string[]): Conversation {
  const base = Date.now() - daysAgo * 86_400_000;
  let t = base;
  const step = () => (t += 45_000);

  const turns = questions.map((q) => {
    const askedAt = new Date(step()).toISOString();
    const { content, meta } = replyFor(q);
    return {
      id: newTurnId(),
      status: 'complete' as const,
      human: { id: newMessageId(), role: 'human' as const, content: q, createdAt: askedAt },
      ai: {
        id: newMessageId(),
        role: 'ai' as const,
        content,
        createdAt: new Date(step()).toISOString(),
        meta,
      },
    };
  });

  return {
    id: newConversationId(),
    title: titleFromQuestion(questions[0]),
    createdAt: new Date(base).toISOString(),
    updatedAt: turns.at(-1)!.ai!.createdAt,
    turns,
  };
}
