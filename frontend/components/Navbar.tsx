"use client";

/**
 * T048: Navbar component with user info and logout button
 * T072: Responsive breakpoints (hamburger menu on mobile, full nav on desktop)
 * T073: ARIA labels for accessibility
 *
 * Displays application navigation, user information,
 * and provides logout functionality.
 */

import { useSession, signOut } from "@/lib/auth-client";
import { useRouter, usePathname } from "next/navigation";
import { useState } from "react";

export function Navbar() {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const [loggingOut, setLoggingOut] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await signOut();
      router.push("/signin");
    } catch (error) {
      console.error("Logout failed:", error);
      setLoggingOut(false);
    }
  };

  return (
    <nav className="bg-white/80 dark:bg-gray-900/80 backdrop-blur-md shadow-lg border-b border-indigo-100 dark:border-indigo-900/50" aria-label="Main navigation">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-18">
          {/* Logo/Title */}
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-md">
                <span className="text-xl">✨</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Todo AI
              </h1>
            </div>
            {/* T071: Navigation Links */}
            {session?.user && pathname !== '/chat' && (
              <div className="hidden md:flex items-center gap-2">
                <a
                  href="/chat"
                  className="px-4 py-2 text-sm font-semibold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded-lg transition-all duration-200"
                >
                  💬 Chat
                </a>
              </div>
            )}
          </div>

          {/* Desktop navigation - hidden on mobile */}
          <div className="hidden md:flex items-center gap-3 sm:gap-4">
            {isPending ? (
              <div className="text-sm text-gray-500 dark:text-gray-400" role="status" aria-live="polite">
                Loading...
              </div>
            ) : session?.user ? (
              <>
                <div className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-lg border border-indigo-100 dark:border-indigo-800">
                  <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-semibold text-sm">
                    {(session.user.email?.charAt(0) || session.user.name?.charAt(0) || "U").toUpperCase()}
                  </div>
                  <div className="text-xs sm:text-sm">
                    <span className="text-gray-600 dark:text-gray-400 block text-xs">Signed in</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {session.user.email || session.user.name || "User"}
                    </span>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="px-4 py-2 text-sm font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 border border-red-200 dark:border-red-800"
                  aria-label="Sign out of your account"
                >
                  {loggingOut ? "Logging out..." : "Logout"}
                </button>
              </>
            ) : (
              <a
                href="/signin"
                className="px-5 py-2.5 text-sm font-semibold text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all duration-200 shadow-md hover:shadow-lg hover:scale-105"
                aria-label="Sign in to your account"
              >
                Sign In
              </a>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition-all duration-200"
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle mobile menu"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="2"
                stroke="currentColor"
                aria-hidden="true"
              >
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu - shown when hamburger is clicked */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-indigo-100 dark:border-indigo-900/50 py-4 bg-gradient-to-b from-indigo-50/50 to-transparent dark:from-indigo-900/20" role="menu" aria-label="Mobile navigation menu">
            {isPending ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 px-2" role="status" aria-live="polite">
                Loading...
              </div>
            ) : session?.user ? (
              <div className="space-y-4">
                {/* Mobile navigation links */}
                {pathname !== '/chat' && (
                  <div className="space-y-2 px-2">
                    <a
                      href="/chat"
                      className="flex items-center gap-2 px-4 py-3 rounded-xl text-base font-semibold text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-all duration-200"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <span>💬</span>
                      <span>Chat</span>
                    </a>
                  </div>
                )}
                <div className="px-2">
                  <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-900/30 dark:to-purple-900/30 rounded-xl border border-indigo-100 dark:border-indigo-800">
                    <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold">
                      {(session.user.email?.charAt(0) || session.user.name?.charAt(0) || "U").toUpperCase()}
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-600 dark:text-gray-400 block text-xs">Signed in</span>
                      <span className="font-semibold text-gray-900 dark:text-white block mt-0.5">
                        {session.user.email || session.user.name || "User"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="px-2">
                  <button
                    onClick={() => {
                      setMobileMenuOpen(false);
                      handleLogout();
                    }}
                    disabled={loggingOut}
                    className="w-full px-4 py-3 text-sm font-semibold text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-xl hover:bg-red-100 dark:hover:bg-red-900/30 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 border border-red-200 dark:border-red-800"
                    aria-label="Sign out of your account"
                    role="menuitem"
                  >
                    {loggingOut ? "Logging out..." : "Logout"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="px-2">
                <a
                  href="/signin"
                  className="block w-full px-4 py-3 text-sm font-semibold text-center text-white bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl hover:from-indigo-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all duration-200 shadow-md"
                  aria-label="Sign in to your account"
                  role="menuitem"
                >
                  Sign In
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
