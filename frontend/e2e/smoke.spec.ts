import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { USER, chatResult, signedIn, sse, withEvaluationReport } from "./mock-api";

async function expectNoA11yViolations(page: Page) {
  const { violations } = await new AxeBuilder({ page }).analyze();
  expect(violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length})`)).toEqual([]);
}

test("login page is accessible and signs the user in", async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/login")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ access_token: "e2e-token", token_type: "bearer", user: USER }),
      });
    }
    if (path.endsWith("/auth/me")) return route.fulfill({ contentType: "application/json", body: JSON.stringify(USER) });
    return route.fulfill({ contentType: "application/json", body: "{}" });
  });
  await page.goto("/login/");
  await expect(page.getByRole("heading", { level: 1, name: "Welcome back" })).toBeVisible();
  await expectNoA11yViolations(page);

  await page.getByPlaceholder("you@example.com").fill("e2e@example.com");
  await page.getByPlaceholder("Enter your password").fill("Password-123");
  await page.getByRole("button", { name: "Show password" }).click();
  await expect(page.getByPlaceholder("Enter your password")).toHaveAttribute("type", "text");
  await page.locator("form").getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard\/?$/);
});

for (const theme of ["light", "dark"] as const) {
  test(`dashboard pages have no accessibility violations (${theme})`, async ({ page }) => {
    await signedIn(page, theme);
    for (const path of ["/dashboard/", "/dashboard/chat/", "/dashboard/documents/"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoA11yViolations(page);
    }
  });
}

test("chat streams the answer and shows its source", async ({ page }) => {
  await signedIn(page);
  await page.route("**/api/v1/chat/stream", (route) =>
    route.fulfill({
      contentType: "text/event-stream",
      body: sse([
        ["step", { node: "retrieve", execution_time_ms: 40, decision: null, output: "3 chunks" }],
        ["token", { text: "Customers may request " }],
        ["token", { text: "a refund within 30 days [Source 1]." }],
        ["result", chatResult()],
      ]),
    })
  );
  await page.goto("/dashboard/chat/");
  await page.getByPlaceholder("Ask a question about your documents").fill("What is the refund window?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Customers may request a refund within 30 days").first()).toBeVisible();
  await expect(page.getByText("refund_policy.pdf").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy answer" })).toBeVisible();
});

test("a clarifying question offers Answer anyway, which re-asks without the check", async ({ page }) => {
  await signedIn(page);
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/v1/chat/stream", (route) => {
    bodies.push(route.request().postDataJSON());
    const first = bodies.length === 1;
    const result = first
      ? chatResult({
          answer: "I don't have enough evidence to answer this question reliably.",
          confidence: 0,
          confidence_level: "LOW",
          clarification_needed: true,
          clarification_question: "Which policy do you mean?",
          citations: [],
        })
      : chatResult();
    return route.fulfill({ contentType: "text/event-stream", body: sse([["result", result]]) });
  });
  await page.goto("/dashboard/chat/");
  await page.getByPlaceholder("Ask a question about your documents").fill("Tell me about the policy");
  await page.getByRole("button", { name: "Send question" }).click();
  await page.getByRole("button", { name: "Answer anyway" }).click();
  await expect(page.getByText("within 30 days").first()).toBeVisible();
  expect(bodies[1]).toMatchObject({ question: "Tell me about the policy", skip_clarification: true });
});

test("the chat offers starter questions drawn from the user's documents", async ({ page }) => {
  await signedIn(page);
  await page.route("**/api/v1/chat/stream", (route) =>
    route.fulfill({ contentType: "text/event-stream", body: sse([["result", chatResult()]]) })
  );
  await page.goto("/dashboard/chat/");
  await expect(page.getByRole("heading", { name: "What would you like to know?" })).toBeVisible();
  await page.getByRole("button", { name: "Summarize refund policy" }).click();
  await expect(page.getByText("within 30 days").first()).toBeVisible();
});

test("a question typed on the dashboard is asked in the chat; source markers become clickable badges", async ({ page }) => {
  await signedIn(page);
  const bodies: Record<string, unknown>[] = [];
  await page.route("**/api/v1/chat/stream", (route) => {
    bodies.push(route.request().postDataJSON());
    return route.fulfill({
      contentType: "text/event-stream",
      body: sse([["result", chatResult({ citations: [{ document_id: "d1", filename: "refund_policy.pdf", chunk_id: "c1", page: 2, text: "Refunds within 30 days.", source: 1 }] })]]),
    });
  });
  await page.goto("/dashboard/");
  await page.getByLabel("Ask a question about your documents").fill("What is the refund window?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard\/chat\/?$/);
  await expect(page.getByText("within 30 days").first()).toBeVisible();
  expect(bodies).toHaveLength(1);
  expect(bodies[0]).toMatchObject({ question: "What is the refund window?" });

  await page.getByRole("button", { name: "Open source 1" }).click();
  await expect(page.getByText("Refunds within 30 days.").first()).toBeVisible();
});

for (const theme of ["light", "dark"] as const) {
  test(`the evaluation report shows behaviour, scores and every question (${theme})`, async ({ page }) => {
    await withEvaluationReport(page, theme);
    await page.goto("/dashboard/evaluation/");
    await expect(page.getByRole("heading", { name: "Does it behave correctly?" })).toBeVisible();
    await expect(page.getByText("Same as plain RAG").first()).toBeVisible();
    await expect(page.getByText("1 more than plain RAG").first()).toBeVisible();
    await expect(page.getByRole("note")).toContainText("raw retrieved text"); // the fallback answer in question 2
    await expect(page.getByRole("row", { name: /Faithfulness/ })).toContainText("81.0%");
    await page.getByRole("button", { name: /What is the deadline\?/ }).click();
    await expect(page.getByText("Which deadline do you mean?")).toBeVisible();
    await expectNoA11yViolations(page);
  });
}
