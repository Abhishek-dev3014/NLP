"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Download, Info, Trash2 } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { ConfirmDialog } from "./ui/dialog";
import { ErrorState, PageHeading } from "./common";
import { ThemeToggle } from "./theme-toggle";
export function Settings() {
  const client = useQueryClient();
  const [message, setMessage] = useState("");
  const deletion = useMutation({
    mutationFn: api.clear,
    onSuccess: async () => {
      await client.invalidateQueries();
      setMessage("Your session history has been permanently deleted.");
    },
  });
  const exportData = useMutation({
    mutationFn: async () => {
      let page = 1;
      const all = [];
      while (true) {
        const response = await api.analyses(
          new URLSearchParams({ page: String(page), page_size: "50" }),
        );
        all.push(...response.items);
        if (all.length >= response.total) break;
        page++;
      }
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(all, null, 2)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "verifact-session-history.json";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(`Exported ${all.length} analyses.`);
    },
  });
  return (
    <>
      <PageHeading
        eyebrow="YOUR WORKSPACE, YOUR CONTROL"
        title="Settings & privacy"
        description="Manage your appearance, understand your data, and take control of your research history."
      />
      <div className="settings-section">
        {(deletion.isError || exportData.isError) && (
          <ErrorState
            message={deletion.error?.message || exportData.error?.message || ""}
          />
        )}
        <section className="panel">
          <div className="setting-row">
            <div>
              <h3>Appearance</h3>
              <p>
                Switch between dark and light themes. Your preference is saved
                in this browser.
              </p>
            </div>
            <ThemeToggle />
          </div>
          <div className="setting-row">
            <div>
              <h3>Anonymous session</h3>
              <p>
                A signed, HttpOnly browser cookie scopes your history. Clearing
                the cookie loses access to those records. This app does not
                provide account recovery or cross-device sync.
              </p>
            </div>
            <span className="method-tag">No account</span>
          </div>
          <div className="setting-row">
            <div>
              <h3>Export your data</h3>
              <p>
                Download all reports accessible to this session as JSON,
                including article text, actual predictions, and observations.
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              disabled={exportData.isPending}
              onClick={() => exportData.mutate()}
            >
              <Download size={13} />
              {exportData.isPending ? "Exporting…" : "Export data"}
            </Button>
          </div>
          <div className="setting-row">
            <div>
              <h3>Delete session history</h3>
              <p>
                Permanently remove your stored analyses and their related
                insights, claims, and evidence. Original upload files are never
                saved.
              </p>
            </div>
            <ConfirmDialog
              title="Delete all your analyses?"
              description="All article text and analysis results belonging to this browser session will be permanently removed. This action cannot be undone."
              onConfirm={() => deletion.mutate()}
              pending={deletion.isPending}
              trigger={
                <Button
                  size="sm"
                  variant="outline"
                  disabled={deletion.isPending}
                >
                  <Trash2 size={13} /> Delete history
                </Button>
              }
            />
          </div>
          <div className="setting-row">
            <div>
              <h3>External evidence & model configuration</h3>
              <p>
                Evidence search is disabled by default. When configured, each
                analysis asks for consent before sending the headline or
                candidate claim to Google. Model and database settings are
                server-managed environment variables.
              </p>
            </div>
          </div>
        </section>
        {message && (
          <p className="success-message mt-4" role="status">
            {message}
          </p>
        )}
        <div className="transparency-note">
          <Info size={16} />
          <p>
            Article content is stored as plain text in the configured database.
            For shared deployments, use HTTPS, secure cookies, a stable secret,
            a protected PostgreSQL instance, and a documented retention policy.
            Read the deployment guidance in the README.
          </p>
        </div>
        <Link href="/model-performance" className="section-link mt-6">
          Review model transparency <ArrowUpRight size={12} />
        </Link>
      </div>
    </>
  );
}
