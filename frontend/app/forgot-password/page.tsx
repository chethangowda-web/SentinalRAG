"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Mail } from "lucide-react";
import { AuthShell } from "@/components/shared/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { forgotPassword, getAuthConfig } from "@/services/auth";
import toast from "react-hot-toast";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    getAuthConfig()
      .then((c) => setAvailable(c.password_reset_available))
      .catch(() => setAvailable(true)); // let the request itself report the problem
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    try {
      await forgotPassword(email.trim());
      setSent(true);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not send the reset link");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Reset your password" description="We will email you a link to choose a new one">
      {available === false ? (
        <p role="status" className="text-sm text-muted-foreground">
          Password reset by email is not set up on this server. Ask the person who runs it to reset your password.
        </p>
      ) : sent ? (
        <div role="status" className="space-y-3 text-sm">
          <p>
            If an account exists for <strong>{email}</strong>, a reset link is on its way. It works once and expires in an hour.
          </p>
          <p className="text-muted-foreground">Nothing in your inbox? Check the spam folder, or try again in a few minutes.</p>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="reset-email" className="text-sm font-medium">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
              <Input
                id="reset-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10"
                required
              />
            </div>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Sending..." : "Send reset link"}
          </Button>
        </form>
      )}
      <p className="mt-4 text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary hover:underline">Back to sign in</Link>
      </p>
    </AuthShell>
  );
}
