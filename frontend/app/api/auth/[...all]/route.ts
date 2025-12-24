import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

/**
 * Better Auth API route handler for Next.js App Router.
 *
 * This catch-all route handles all Better Auth endpoints:
 * - POST /api/auth/sign-up/email
 * - POST /api/auth/sign-in/email
 * - POST /api/auth/sign-out
 * - GET  /api/auth/get-session
 * - POST /api/auth/token (JWT endpoint)
 * - And more...
 *
 * The handler automatically processes incoming requests and
 * returns appropriate responses based on Better Auth's logic.
 */
export const { GET, POST } = toNextJsHandler(auth);
