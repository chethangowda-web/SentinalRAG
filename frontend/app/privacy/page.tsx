import type { Metadata } from "next";
import { LegalPage } from "@/components/shared/LegalPage";

export const metadata: Metadata = { title: "Privacy notice" };

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy notice"
      updated="17 October 2026"
      intro="SentinelRAG answers questions about the documents you upload. This page says what it keeps, who else sees it, and how to remove it."
      sections={[
        {
          heading: "What is stored",
          body: (
            <>
              <p>Your name and email address, and your password as a salted hash (the password itself is never stored).</p>
              <p>
                The documents you upload: their extracted text, the passages it is split into, and the numeric
                embeddings used to search them. Your questions, the answers, and technical traces of how each answer was
                produced (timings, which passages were used).
              </p>
            </>
          ),
        },
        {
          heading: "Who else processes it",
          body: (
            <>
              <p>
                <strong>The AI provider.</strong> To write an answer, your question and the few most relevant passages
                of your documents are sent to the AI provider the operator has configured (Google Gemini by default).
                The provider&apos;s own terms apply to that processing. On a provider&apos;s free tier, submitted content
                may be used to improve its products, so do not upload confidential or personal data unless the operator
                has confirmed a paid tier with data protection.
              </p>
              <p>
                <strong>Hosting.</strong> The service, its database and its search index run on the operator&apos;s hosting
                provider (Railway by default).
              </p>
              <p>
                <strong>Email.</strong> If password reset is enabled, your email address is passed to the email provider
                only to deliver the reset link.
              </p>
              <p>There are no advertising or analytics trackers, and your data is not sold.</p>
            </>
          ),
        },
        {
          heading: "Your browser",
          body: <p>The site stores your sign-in token and your light or dark theme choice in your browser. It sets no tracking cookies.</p>,
        },
        {
          heading: "Keeping and deleting your data",
          body: (
            <p>
              You can delete any document from the Documents page, and delete your whole account from Profile, which
              permanently removes your documents, search index entries, chats and evaluations. Backups, where the operator
              keeps them, age out on their own schedule.
            </p>
          ),
        },
        {
          heading: "Security",
          body: (
            <p>
              Traffic is encrypted in transit. Each account can only search its own documents. Sign-in attempts and sign-ups are
              rate limited, and changing or resetting your password signs every other device out. No system is perfectly secure:
              do not upload anything you could not afford to have exposed.
            </p>
          ),
        },
        {
          heading: "Questions",
          body: <p>Ask the person or organisation that runs this deployment of SentinelRAG: they are responsible for your data here.</p>,
        },
      ]}
    />
  );
}
