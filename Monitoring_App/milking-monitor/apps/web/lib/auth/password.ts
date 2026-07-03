import { randomBytes, scryptSync, timingSafeEqual } from "crypto";

const KEY_LENGTH = 64;
const SALT_LENGTH = 32;

export function hashPassword(password: string): string {
  const salt = randomBytes(SALT_LENGTH).toString("hex");
  const derivedKey = scryptSync(password, salt, KEY_LENGTH, { N: 16384, r: 8, p: 1 });
  return `${salt}:${derivedKey.toString("hex")}`;
}

export function verifyPassword(password: string, storedHash: string): boolean {
  const [salt, keyHex] = storedHash.split(":");
  if (!salt || !keyHex) return false;

  const key = Buffer.from(keyHex, "hex");
  const derivedKey = scryptSync(password, salt, key.length, { N: 16384, r: 8, p: 1 });

  return timingSafeEqual(key, derivedKey);
}
