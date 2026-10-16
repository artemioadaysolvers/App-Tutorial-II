export const MAX_MESSAGE_LENGTH = 2000;
export const fields = ['mensaje1', 'mensaje2', 'mensaje3'] as const;
export type MessageKey = (typeof fields)[number];

export function validateMessages(values: Record<MessageKey, string>) {
  const errors: Partial<Record<MessageKey, string>> = {};
  for (const field of fields) {
    const value = values[field].trim();
    if (!value) errors[field] = 'Escribe un mensaje para continuar.';
    else if (value.length > MAX_MESSAGE_LENGTH) errors[field] = `Usa hasta ${MAX_MESSAGE_LENGTH} caracteres.`;
  }
  return errors;
}
