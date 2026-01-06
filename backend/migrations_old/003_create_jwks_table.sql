-- Better Auth JWT Plugin JWKS Table
-- Migration: 003_create_jwks_table.sql
-- This creates the jwks table required by the JWT plugin for storing web keys

-- JWKS table: stores JWT signing keys (JSON Web Key Set)
CREATE TABLE IF NOT EXISTS "jwks" (
  "id" TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  "publicKey" TEXT NOT NULL,
  "privateKey" TEXT NOT NULL,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW(),
  "expiresAt" TIMESTAMP
);
