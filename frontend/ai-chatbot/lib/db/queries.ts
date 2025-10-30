import "server-only";

import {
  and,
  asc,
  count,
  desc,
  eq,
  gt,
  gte,
  inArray,
  lt,
  type SQL,
} from "drizzle-orm";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import type { ArtifactKind } from "@/components/artifact";
import type { VisibilityType } from "@/components/visibility-selector";
import { ChatSDKError } from "../errors";
import type { AppUsage } from "../usage";
import { generateUUID } from "../utils";
import {
  type Chat,
  chat,
  type DBMessage,
  document,
  message,
  type Suggestion,
  stream,
  suggestion,
  type User,
  user,
  vote,
} from "./schema";
import { generateHashedPassword } from "./utils";

const useInMemoryDb = Boolean(
  process.env.PLAYWRIGHT ||
    process.env.PLAYWRIGHT_TEST_BASE_URL ||
    process.env.CI_PLAYWRIGHT,
);

let db: ReturnType<typeof drizzle> | undefined;

if (!useInMemoryDb) {
  const connectionString = process.env.POSTGRES_URL;
  if (!connectionString) {
    throw new Error(
      "POSTGRES_URL must be configured unless the in-memory Playwright database is enabled",
    );
  }
  const client = postgres(connectionString);
  db = drizzle(client);
}

type MemoryUser = User;
type MemoryChat = Chat & { lastContext?: AppUsage | null };
type MemoryMessage = DBMessage;
type MemoryDocument = {
  id: string;
  title: string;
  kind: ArtifactKind;
  content: string;
  userId: string;
  createdAt: Date;
};
type MemorySuggestion = Suggestion;
type MemoryStream = { id: string; chatId: string; createdAt: Date };
type MemoryVote = { chatId: string; messageId: string; isUpvoted: boolean };

const memoryStore = useInMemoryDb
  ? {
      users: new Map<string, MemoryUser>(),
      userEmails: new Map<string, string>(),
      chats: new Map<string, MemoryChat>(),
      messages: new Map<string, MemoryMessage>(),
      chatMessages: new Map<string, string[]>(),
      documents: new Map<string, MemoryDocument[]>(),
      suggestions: new Map<string, MemorySuggestion[]>(),
      streams: new Map<string, MemoryStream>(),
      votes: new Map<string, MemoryVote>(),
    }
  : undefined;

function memoryUpsertChatMessageReference(chatId: string, messageId: string) {
  if (!memoryStore) {
    return;
  }
  const references = memoryStore.chatMessages.get(chatId) ?? [];
  references.push(messageId);
  memoryStore.chatMessages.set(chatId, references);
}

function memoryRemoveChatMessageReference(chatId: string, messageId: string) {
  if (!memoryStore) {
    return;
  }
  const references = memoryStore.chatMessages.get(chatId);
  if (!references) {
    return;
  }
  memoryStore.chatMessages.set(
    chatId,
    references.filter((currentId) => currentId !== messageId),
  );
}

function memorySortChatsDescending(chats: MemoryChat[]): MemoryChat[] {
  return [...chats].sort(
    (first, second) => second.createdAt.getTime() - first.createdAt.getTime(),
  );
}

function memorySortMessagesAscending(messages: MemoryMessage[]): MemoryMessage[] {
  return [...messages].sort(
    (first, second) => first.createdAt.getTime() - second.createdAt.getTime(),
  );
}

function memorySortDocumentsAscending(documents: MemoryDocument[]): MemoryDocument[] {
  return [...documents].sort(
    (first, second) => first.createdAt.getTime() - second.createdAt.getTime(),
  );
}

function memoryFindUserByEmail(email: string): MemoryUser | undefined {
  if (!memoryStore) {
    return undefined;
  }
  const userId = memoryStore.userEmails.get(email);
  if (!userId) {
    return undefined;
  }
  return memoryStore.users.get(userId);
}

function memoryPersistUser(user: MemoryUser): void {
  if (!memoryStore) {
    return;
  }
  memoryStore.users.set(user.id, user);
  memoryStore.userEmails.set(user.email, user.id);
}

async function memoryGetUser(email: string): Promise<User[]> {
  const record = memoryFindUserByEmail(email);
  return record ? [record] : [];
}

async function memoryCreateUser(email: string, password: string) {
  if (!memoryStore) {
    return;
  }
  if (memoryFindUserByEmail(email)) {
    throw new ChatSDKError("bad_request:database", "Failed to create user");
  }
  const userRecord: MemoryUser = {
    id: generateUUID(),
    email,
    password: generateHashedPassword(password),
  };
  memoryPersistUser(userRecord);
}

async function memoryCreateGuestUser() {
  if (!memoryStore) {
    return [] as { id: string; email: string }[];
  }
  const id = generateUUID();
  const email = `guest-${Date.now()}-${id}`;
  const guest: MemoryUser = {
    id,
    email,
    password: generateHashedPassword(generateUUID()),
  };
  memoryPersistUser(guest);
  return [{ id: guest.id, email: guest.email }];
}

async function memorySaveChat(args: {
  id: string;
  userId: string;
  title: string;
  visibility: VisibilityType;
}) {
  if (!memoryStore) {
    return;
  }
  const record: MemoryChat = {
    id: args.id,
    createdAt: new Date(),
    userId: args.userId,
    title: args.title,
    visibility: args.visibility,
    lastContext: null,
  };
  memoryStore.chats.set(record.id, record);
}

async function memoryDeleteChatById(id: string) {
  if (!memoryStore) {
    return null;
  }
  const record = memoryStore.chats.get(id) ?? null;
  if (!record) {
    return null;
  }
  memoryStore.chats.delete(id);
  const messageIds = memoryStore.chatMessages.get(id) ?? [];
  for (const messageId of messageIds) {
    memoryStore.messages.delete(messageId);
    memoryStore.votes.delete(`${id}:${messageId}`);
  }
  memoryStore.chatMessages.delete(id);
  for (const streamEntry of memoryStore.streams.values()) {
    if (streamEntry.chatId === id) {
      memoryStore.streams.delete(streamEntry.id);
    }
  }
  return record;
}

async function memoryDeleteAllChatsByUserId(userId: string) {
  if (!memoryStore) {
    return { deletedCount: 0 };
  }
  let deletedCount = 0;
  for (const chatRecord of [...memoryStore.chats.values()]) {
    if (chatRecord.userId !== userId) {
      continue;
    }
    await memoryDeleteChatById(chatRecord.id);
    deletedCount += 1;
  }
  return { deletedCount };
}

async function memoryGetChatsByUserId({
  id,
  limit,
  startingAfter,
  endingBefore,
}: {
  id: string;
  limit: number;
  startingAfter: string | null;
  endingBefore: string | null;
}) {
  if (!memoryStore) {
    return { chats: [], hasMore: false };
  }
  const userChats = memorySortChatsDescending(
    [...memoryStore.chats.values()].filter((chatRecord) => chatRecord.userId === id),
  );

  let filtered = userChats;
  if (startingAfter) {
    const reference = memoryStore.chats.get(startingAfter);
    if (!reference) {
      throw new ChatSDKError(
        "not_found:database",
        `Chat with id ${startingAfter} not found`,
      );
    }
    filtered = filtered.filter(
      (candidate) => candidate.createdAt.getTime() > reference.createdAt.getTime(),
    );
  } else if (endingBefore) {
    const reference = memoryStore.chats.get(endingBefore);
    if (!reference) {
      throw new ChatSDKError(
        "not_found:database",
        `Chat with id ${endingBefore} not found`,
      );
    }
    filtered = filtered.filter(
      (candidate) => candidate.createdAt.getTime() < reference.createdAt.getTime(),
    );
  }

  const hasMore = filtered.length > limit;
  return {
    chats: filtered.slice(0, limit),
    hasMore,
  };
}

async function memoryGetChatById(id: string) {
  if (!memoryStore) {
    return null;
  }
  return memoryStore.chats.get(id) ?? null;
}

async function memorySaveMessages({ messages }: { messages: DBMessage[] }) {
  if (!memoryStore) {
    return [] as DBMessage[];
  }
  for (const record of messages) {
    const normalized: MemoryMessage = {
      ...record,
      createdAt: new Date(record.createdAt),
    };
    memoryStore.messages.set(normalized.id, normalized);
    memoryUpsertChatMessageReference(normalized.chatId, normalized.id);
  }
  return messages;
}

async function memoryGetMessagesByChatId(id: string) {
  if (!memoryStore) {
    return [] as DBMessage[];
  }
  const messageIds = memoryStore.chatMessages.get(id) ?? [];
  const messages = messageIds
    .map((messageId) => memoryStore!.messages.get(messageId))
    .filter((candidate): candidate is MemoryMessage => Boolean(candidate));
  return memorySortMessagesAscending(messages);
}

async function memoryVoteMessage({
  chatId,
  messageId,
  type,
}: {
  chatId: string;
  messageId: string;
  type: "up" | "down";
}) {
  if (!memoryStore) {
    return;
  }
  const key = `${chatId}:${messageId}`;
  memoryStore.votes.set(key, { chatId, messageId, isUpvoted: type === "up" });
}

async function memoryGetVotesByChatId(id: string) {
  if (!memoryStore) {
    return [] as MemoryVote[];
  }
  return [...memoryStore.votes.values()].filter(
    (voteRecord) => voteRecord.chatId === id,
  );
}

async function memorySaveDocument({
  id,
  title,
  kind,
  content,
  userId,
}: {
  id: string;
  title: string;
  kind: ArtifactKind;
  content: string;
  userId: string;
}) {
  if (!memoryStore) {
    return [] as MemoryDocument[];
  }
  const entry: MemoryDocument = {
    id,
    title,
    kind,
    content,
    userId,
    createdAt: new Date(),
  };
  const documents = memoryStore.documents.get(id) ?? [];
  documents.push(entry);
  memoryStore.documents.set(id, documents);
  return [entry];
}

async function memoryGetDocumentsById(id: string) {
  if (!memoryStore) {
    return [] as MemoryDocument[];
  }
  return memorySortDocumentsAscending(memoryStore.documents.get(id) ?? []);
}

async function memoryGetDocumentById(id: string) {
  const documents = await memoryGetDocumentsById(id);
  return documents.at(-1) ?? null;
}

async function memoryDeleteDocumentsByIdAfterTimestamp({
  id,
  timestamp,
}: {
  id: string;
  timestamp: Date;
}) {
  if (!memoryStore) {
    return [] as MemoryDocument[];
  }
  const current = memoryStore.documents.get(id) ?? [];
  const kept: MemoryDocument[] = [];
  const removed: MemoryDocument[] = [];
  for (const documentRecord of current) {
    if (documentRecord.createdAt > timestamp) {
      removed.push(documentRecord);
    } else {
      kept.push(documentRecord);
    }
  }
  memoryStore.documents.set(id, kept);
  if (removed.length > 0) {
    const suggestions = memoryStore.suggestions.get(id) ?? [];
    memoryStore.suggestions.set(
      id,
      suggestions.filter((candidate) => candidate.documentCreatedAt <= timestamp),
    );
  }
  return removed;
}

async function memorySaveSuggestions({
  suggestions,
}: {
  suggestions: Suggestion[];
}) {
  if (!memoryStore) {
    return [] as Suggestion[];
  }
  for (const entry of suggestions) {
    const bucket = memoryStore.suggestions.get(entry.documentId) ?? [];
    bucket.push(entry);
    memoryStore.suggestions.set(entry.documentId, bucket);
  }
  return suggestions;
}

async function memoryGetSuggestionsByDocumentId({
  documentId,
}: {
  documentId: string;
}) {
  if (!memoryStore) {
    return [] as Suggestion[];
  }
  return [...(memoryStore.suggestions.get(documentId) ?? [])];
}

async function memoryGetMessageById(id: string) {
  if (!memoryStore) {
    return [] as DBMessage[];
  }
  const record = memoryStore.messages.get(id);
  return record ? [record] : [];
}

async function memoryDeleteMessagesByChatIdAfterTimestamp({
  chatId,
  timestamp,
}: {
  chatId: string;
  timestamp: Date;
}) {
  if (!memoryStore) {
    return [] as DBMessage[];
  }
  const messageIds = memoryStore.chatMessages.get(chatId) ?? [];
  const kept: string[] = [];
  const removed: DBMessage[] = [];
  for (const messageId of messageIds) {
    const record = memoryStore.messages.get(messageId);
    if (!record) {
      continue;
    }
    if (record.createdAt >= timestamp) {
      removed.push(record);
      memoryStore.messages.delete(messageId);
      memoryStore.votes.delete(`${chatId}:${messageId}`);
    } else {
      kept.push(messageId);
    }
  }
  memoryStore.chatMessages.set(chatId, kept);
  return removed;
}

async function memoryUpdateChatVisibilityById({
  chatId,
  visibility,
}: {
  chatId: string;
  visibility: "private" | "public";
}) {
  if (!memoryStore) {
    return;
  }
  const record = memoryStore.chats.get(chatId);
  if (!record) {
    return;
  }
  record.visibility = visibility;
  memoryStore.chats.set(chatId, record);
}

async function memoryUpdateChatLastContextById({
  chatId,
  context,
}: {
  chatId: string;
  context: AppUsage;
}) {
  if (!memoryStore) {
    return;
  }
  const record = memoryStore.chats.get(chatId);
  if (!record) {
    return;
  }
  record.lastContext = context;
  memoryStore.chats.set(chatId, record);
}

async function memoryGetMessageCountByUserId({
  id,
  differenceInHours,
}: {
  id: string;
  differenceInHours: number;
}) {
  if (!memoryStore) {
    return 0;
  }
  const threshold = Date.now() - differenceInHours * 60 * 60 * 1000;
  let countResult = 0;
  for (const messageRecord of memoryStore.messages.values()) {
    const chatRecord = memoryStore.chats.get(messageRecord.chatId);
    if (!chatRecord || chatRecord.userId !== id) {
      continue;
    }
    if (messageRecord.role === "user" && messageRecord.createdAt.getTime() >= threshold) {
      countResult += 1;
    }
  }
  return countResult;
}

async function memoryCreateStreamId({
  streamId,
  chatId,
}: {
  streamId: string;
  chatId: string;
}) {
  if (!memoryStore) {
    return;
  }
  memoryStore.streams.set(streamId, {
    id: streamId,
    chatId,
    createdAt: new Date(),
  });
}

async function memoryGetStreamIdsByChatId({ chatId }: { chatId: string }) {
  if (!memoryStore) {
    return [] as string[];
  }
  return [...memoryStore.streams.values()]
    .filter((streamRecord) => streamRecord.chatId === chatId)
    .sort((first, second) => first.createdAt.getTime() - second.createdAt.getTime())
    .map((streamRecord) => streamRecord.id);
}


export async function getUser(email: string): Promise<User[]> {
  if (useInMemoryDb) {
    return memoryGetUser(email);
  }
  const database = db!;
  try {
    return await database.select().from(user).where(eq(user.email, email));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get user by email"
    );
  }
}

export async function createUser(email: string, password: string) {
  if (useInMemoryDb) {
    return memoryCreateUser(email, password);
  }
  const hashedPassword = generateHashedPassword(password);

  try {
    return await db!.insert(user).values({ email, password: hashedPassword });
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to create user");
  }
}

export async function createGuestUser() {
  if (useInMemoryDb) {
    return memoryCreateGuestUser();
  }
  const email = `guest-${Date.now()}`;
  const password = generateHashedPassword(generateUUID());

  try {
    return await db!.insert(user).values({ email, password }).returning({
      id: user.id,
      email: user.email,
    });
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to create guest user"
    );
  }
}

export async function saveChat({
  id,
  userId,
  title,
  visibility,
}: {
  id: string;
  userId: string;
  title: string;
  visibility: VisibilityType;
}) {
  if (useInMemoryDb) {
    return memorySaveChat({ id, userId, title, visibility });
  }
  try {
    return await db!.insert(chat).values({
      id,
      createdAt: new Date(),
      userId,
      title,
      visibility,
    });
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to save chat");
  }
}

export async function deleteChatById({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryDeleteChatById(id);
  }
  try {
    await db!.delete(vote).where(eq(vote.chatId, id));
    await db!.delete(message).where(eq(message.chatId, id));
    await db!.delete(stream).where(eq(stream.chatId, id));

    const [chatsDeleted] = await db!
      .delete(chat)
      .where(eq(chat.id, id))
      .returning();
    return chatsDeleted;
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to delete chat by id"
    );
  }
}

export async function deleteAllChatsByUserId({ userId }: { userId: string }) {
  if (useInMemoryDb) {
    return memoryDeleteAllChatsByUserId(userId);
  }
  try {
    const userChats = await db!
      .select({ id: chat.id })
      .from(chat)
      .where(eq(chat.userId, userId));

    if (userChats.length === 0) {
      return { deletedCount: 0 };
    }

    const chatIds = userChats.map(c => c.id);

    await db!.delete(vote).where(inArray(vote.chatId, chatIds));
    await db!.delete(message).where(inArray(message.chatId, chatIds));
    await db!.delete(stream).where(inArray(stream.chatId, chatIds));

    const deletedChats = await db!
      .delete(chat)
      .where(eq(chat.userId, userId))
      .returning();

    return { deletedCount: deletedChats.length };
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to delete all chats by user id"
    );
  }
}

export async function getChatsByUserId({
  id,
  limit,
  startingAfter,
  endingBefore,
}: {
  id: string;
  limit: number;
  startingAfter: string | null;
  endingBefore: string | null;
}) {
  if (useInMemoryDb) {
    return memoryGetChatsByUserId({ id, limit, startingAfter, endingBefore });
  }
  try {
    const extendedLimit = limit + 1;

    const query = (whereCondition?: SQL<any>) =>
      db!
        .select()
        .from(chat)
        .where(
          whereCondition
            ? and(whereCondition, eq(chat.userId, id))
            : eq(chat.userId, id)
        )
        .orderBy(desc(chat.createdAt))
        .limit(extendedLimit);

    let filteredChats: Chat[] = [];

    if (startingAfter) {
      const [selectedChat] = await db
        .select()
        .from(chat)
        .where(eq(chat.id, startingAfter))
        .limit(1);

      if (!selectedChat) {
        throw new ChatSDKError(
          "not_found:database",
          `Chat with id ${startingAfter} not found`
        );
      }

      filteredChats = await query(gt(chat.createdAt, selectedChat.createdAt));
    } else if (endingBefore) {
      const [selectedChat] = await db
        .select()
        .from(chat)
        .where(eq(chat.id, endingBefore))
        .limit(1);

      if (!selectedChat) {
        throw new ChatSDKError(
          "not_found:database",
          `Chat with id ${endingBefore} not found`
        );
      }

      filteredChats = await query(lt(chat.createdAt, selectedChat.createdAt));
    } else {
      filteredChats = await query();
    }

    const hasMore = filteredChats.length > limit;

    return {
      chats: hasMore ? filteredChats.slice(0, limit) : filteredChats,
      hasMore,
    };
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get chats by user id"
    );
  }
}

export async function getChatById({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetChatById(id);
  }
  try {
    const [selectedChat] = await db!.select().from(chat).where(eq(chat.id, id));
    if (!selectedChat) {
      return null;
    }

    return selectedChat;
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to get chat by id");
  }
}

export async function saveMessages({ messages }: { messages: DBMessage[] }) {
  if (useInMemoryDb) {
    return memorySaveMessages({ messages });
  }
  try {
    return await db!.insert(message).values(messages);
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to save messages");
  }
}

export async function getMessagesByChatId({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetMessagesByChatId(id);
  }
  try {
    return await db!
      .select()
      .from(message)
      .where(eq(message.chatId, id))
      .orderBy(asc(message.createdAt));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get messages by chat id"
    );
  }
}

export async function voteMessage({
  chatId,
  messageId,
  type,
}: {
  chatId: string;
  messageId: string;
  type: "up" | "down";
}) {
  if (useInMemoryDb) {
    return memoryVoteMessage({ chatId, messageId, type });
  }
  try {
    const [existingVote] = await db!
      .select()
      .from(vote)
      .where(and(eq(vote.messageId, messageId)));

    if (existingVote) {
      return await db!
        .update(vote)
        .set({ isUpvoted: type === "up" })
        .where(and(eq(vote.messageId, messageId), eq(vote.chatId, chatId)));
    }
    return await db!.insert(vote).values({
      chatId,
      messageId,
      isUpvoted: type === "up",
    });
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to vote message");
  }
}

export async function getVotesByChatId({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetVotesByChatId(id);
  }
  try {
    return await db!.select().from(vote).where(eq(vote.chatId, id));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get votes by chat id"
    );
  }
}

export async function saveDocument({
  id,
  title,
  kind,
  content,
  userId,
}: {
  id: string;
  title: string;
  kind: ArtifactKind;
  content: string;
  userId: string;
}) {
  if (useInMemoryDb) {
    return memorySaveDocument({ id, title, kind, content, userId });
  }
  try {
    return await db!
      .insert(document)
      .values({
        id,
        title,
        kind,
        content,
        userId,
        createdAt: new Date(),
      })
      .returning();
  } catch (_error) {
    throw new ChatSDKError("bad_request:database", "Failed to save document");
  }
}

export async function getDocumentsById({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetDocumentsById(id);
  }
  try {
    const documents = await db!
      .select()
      .from(document)
      .where(eq(document.id, id))
      .orderBy(asc(document.createdAt));

    return documents;
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get documents by id"
    );
  }
}

export async function getDocumentById({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetDocumentById(id);
  }
  try {
    const [selectedDocument] = await db!
      .select()
      .from(document)
      .where(eq(document.id, id))
      .orderBy(desc(document.createdAt));

    return selectedDocument;
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get document by id"
    );
  }
}

export async function deleteDocumentsByIdAfterTimestamp({
  id,
  timestamp,
}: {
  id: string;
  timestamp: Date;
}) {
  if (useInMemoryDb) {
    return memoryDeleteDocumentsByIdAfterTimestamp({ id, timestamp });
  }
  try {
    await db!
      .delete(suggestion)
      .where(
        and(
          eq(suggestion.documentId, id),
          gt(suggestion.documentCreatedAt, timestamp)
        )
      );

    return await db!
      .delete(document)
      .where(and(eq(document.id, id), gt(document.createdAt, timestamp)))
      .returning();
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to delete documents by id after timestamp"
    );
  }
}

export async function saveSuggestions({
  suggestions,
}: {
  suggestions: Suggestion[];
}) {
  if (useInMemoryDb) {
    return memorySaveSuggestions({ suggestions });
  }
  try {
    return await db!.insert(suggestion).values(suggestions);
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to save suggestions"
    );
  }
}

export async function getSuggestionsByDocumentId({
  documentId,
}: {
  documentId: string;
}) {
  if (useInMemoryDb) {
    return memoryGetSuggestionsByDocumentId({ documentId });
  }
  try {
    return await db!
      .select()
      .from(suggestion)
      .where(and(eq(suggestion.documentId, documentId)));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get suggestions by document id"
    );
  }
}

export async function getMessageById({ id }: { id: string }) {
  if (useInMemoryDb) {
    return memoryGetMessageById(id);
  }
  try {
    return await db!.select().from(message).where(eq(message.id, id));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get message by id"
    );
  }
}

export async function deleteMessagesByChatIdAfterTimestamp({
  chatId,
  timestamp,
}: {
  chatId: string;
  timestamp: Date;
}) {
  if (useInMemoryDb) {
    return memoryDeleteMessagesByChatIdAfterTimestamp({ chatId, timestamp });
  }
  try {
    const messagesToDelete = await db!
      .select({ id: message.id })
      .from(message)
      .where(
        and(eq(message.chatId, chatId), gte(message.createdAt, timestamp))
      );

    const messageIds = messagesToDelete.map(
      (currentMessage) => currentMessage.id
    );

    if (messageIds.length > 0) {
      await db!
        .delete(vote)
        .where(
          and(eq(vote.chatId, chatId), inArray(vote.messageId, messageIds))
        );

      return await db!
        .delete(message)
        .where(
          and(eq(message.chatId, chatId), inArray(message.id, messageIds))
        );
    }
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to delete messages by chat id after timestamp"
    );
  }
}

export async function updateChatVisiblityById({
  chatId,
  visibility,
}: {
  chatId: string;
  visibility: "private" | "public";
}) {
  if (useInMemoryDb) {
    return memoryUpdateChatVisibilityById({ chatId, visibility });
  }
  try {
    return await db!.update(chat).set({ visibility }).where(eq(chat.id, chatId));
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to update chat visibility by id"
    );
  }
}

export async function updateChatLastContextById({
  chatId,
  context,
}: {
  chatId: string;
  // Store merged server-enriched usage object
  context: AppUsage;
}) {
  if (useInMemoryDb) {
    return memoryUpdateChatLastContextById({ chatId, context });
  }
  try {
    return await db!
      .update(chat)
      .set({ lastContext: context })
      .where(eq(chat.id, chatId));
  } catch (error) {
    console.warn("Failed to update lastContext for chat", chatId, error);
    return;
  }
}

export async function getMessageCountByUserId({
  id,
  differenceInHours,
}: {
  id: string;
  differenceInHours: number;
}) {
  if (useInMemoryDb) {
    return memoryGetMessageCountByUserId({ id, differenceInHours });
  }
  try {
    const twentyFourHoursAgo = new Date(
      Date.now() - differenceInHours * 60 * 60 * 1000
    );

    const [stats] = await db!
      .select({ count: count(message.id) })
      .from(message)
      .innerJoin(chat, eq(message.chatId, chat.id))
      .where(
        and(
          eq(chat.userId, id),
          gte(message.createdAt, twentyFourHoursAgo),
          eq(message.role, "user")
        )
      )
      .execute();

    return stats?.count ?? 0;
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get message count by user id"
    );
  }
}

export async function createStreamId({
  streamId,
  chatId,
}: {
  streamId: string;
  chatId: string;
}) {
  if (useInMemoryDb) {
    return memoryCreateStreamId({ streamId, chatId });
  }
  try {
    await db!
      .insert(stream)
      .values({ id: streamId, chatId, createdAt: new Date() });
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to create stream id"
    );
  }
}

export async function getStreamIdsByChatId({ chatId }: { chatId: string }) {
  if (useInMemoryDb) {
    return memoryGetStreamIdsByChatId({ chatId });
  }
  try {
    const streamIds = await db!
      .select({ id: stream.id })
      .from(stream)
      .where(eq(stream.chatId, chatId))
      .orderBy(asc(stream.createdAt))
      .execute();

    return streamIds.map(({ id }) => id);
  } catch (_error) {
    throw new ChatSDKError(
      "bad_request:database",
      "Failed to get stream ids by chat id"
    );
  }
}
