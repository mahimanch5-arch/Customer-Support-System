/** Short, collision-resistant ids with a readable prefix. */
function rand(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID().replace(/-/g, '').slice(0, 8);
  }
  return Math.random().toString(16).slice(2, 10).padStart(8, '0');
}

export const newConversationId = () => `conv_${rand()}`;
export const newTurnId = () => `turn_${rand()}`;
export const newMessageId = () => `msg_${rand()}`;
