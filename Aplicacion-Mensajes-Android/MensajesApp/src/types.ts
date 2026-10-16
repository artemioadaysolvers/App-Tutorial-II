export type User = { id: string; email: string; name: string };
export type Session = { accessToken: string; tokenType: string; expiresAt: string; user: User };
export type Messages = { mensaje1: string; mensaje2: string; mensaje3: string };
export type SavedMessage = Messages & { id: string; userId: string; createdAt: string };
