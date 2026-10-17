"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { Input } from "@/components/ui/input";
import { changePassword, deleteAccount, logoutEverywhere } from "@/services/auth";
import { clearStoredToken, setStoredToken } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Shield, Mail, Calendar, FileText, MessageSquare, BarChart3, LogOut, Trash2, KeyRound } from "lucide-react";
import toast from "react-hot-toast";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const [deletePassword, setDeletePassword] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changing, setChanging] = useState(false);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChanging(true);
    try {
      const res = await changePassword(currentPassword, newPassword);
      setStoredToken(res.access_token); // this device stays signed in; every other one is signed out
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Password changed. Other devices were signed out.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not change the password");
    } finally {
      setChanging(false);
    }
  };

  const handleLogoutEverywhere = async () => {
    if (!window.confirm("Sign out of every device, including this one?")) return;
    try {
      await logoutEverywhere();
      clearStoredToken();
      window.location.href = "/login";
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not sign out everywhere");
    }
  };

  const handleDeleteAccount = async () => {
    if (!deletePassword) {
      toast.error("Enter your password to confirm");
      return;
    }
    if (!window.confirm("Permanently delete your account, all documents, chats and evaluations? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deleteAccount(deletePassword);
      clearStoredToken();
      window.location.href = "/";
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete the account");
      setDeleting(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Logged out successfully");
    } catch {
      toast.error("Logout failed");
    }
  };

  if (!user) return null;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
        <p className="text-sm text-muted-foreground mt-1">Your account information</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-2xl font-bold text-primary">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <CardTitle className="text-xl">{user.name}</CardTitle>
              <p className="text-sm text-muted-foreground">{user.email}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            <div className="flex items-center gap-3 rounded-lg border p-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Email</p>
                <p className="text-sm font-medium">{user.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border p-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Account Created</p>
                <p className="text-sm font-medium">
                  {user.created_at ? new Date(user.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }) : "N/A"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border p-3">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Total Documents Uploaded</p>
                <p className="text-sm font-medium">{user.total_documents ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border p-3">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Total Chats</p>
                <p className="text-sm font-medium">{user.total_sessions ?? 0}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border p-3">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Total Evaluations</p>
                <p className="text-sm font-medium">{user.total_evaluations ?? 0}</p>
              </div>
            </div>
          </div>

          <Button variant="destructive" className="w-full" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="h-4 w-4" />
            Security
          </CardTitle>
          <p className="text-sm text-muted-foreground">Changing your password signs every other device out.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleChangePassword} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Input
              type="password"
              autoComplete="current-password"
              aria-label="Current password"
              placeholder="Current password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
            <Input
              type="password"
              autoComplete="new-password"
              aria-label="New password"
              placeholder="New password (8+ characters)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              required
            />
            <Button type="submit" disabled={changing || newPassword.length < 8 || !currentPassword}>
              {changing ? "Saving..." : "Change password"}
            </Button>
          </form>
          <Button variant="outline" onClick={handleLogoutEverywhere}>
            Sign out of all devices
          </Button>
        </CardContent>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-red-700 dark:text-red-400">
            <Trash2 className="h-4 w-4" />
            Delete account
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Permanently removes your account, uploaded documents, indexed chunks, chats and evaluations.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row">
          <Input
            type="password"
            placeholder="Confirm with your password"
            aria-label="Password to confirm account deletion"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            className="sm:max-w-xs"
          />
          <Button variant="destructive" onClick={handleDeleteAccount} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete my account"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
