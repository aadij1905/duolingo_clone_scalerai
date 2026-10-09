import { expect, test, type Page } from "@playwright/test";

// A brand-new learner, driven only through the UI: onboarding, then Japanese lesson 1.
// Answers aren't known up front: a miss shows the correct solution, and the missed
// question comes back at the end of the lesson (the warm-up lesson costs no hearts).

async function solvePairs(page: Page) {
  const buttons = page.locator('[class*="pairs"] button');
  const n = (await buttons.count()) / 2;
  const matched = async (i: number) => Number(await buttons.nth(i).evaluate((el) => getComputedStyle(el).opacity)) < 0.6;
  for (let left = 0; left < n; left++) {
    for (let right = n; right < 2 * n && !(await matched(left)); right++) {
      if (await matched(right)) continue;
      await buttons.nth(left).click();
      await buttons.nth(right).click();
      await page.waitForTimeout(700); // flash animation, then the match is recorded
    }
  }
}

test("fresh learner: onboarding → Japanese lesson 1", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/welcome/);
  await page.getByRole("button", { name: /Japanese/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: /Casual/ }).click();
  await page.getByRole("button", { name: "Start lesson 1" }).click();
  await expect(page).toHaveURL(/\/lesson/);
  await expect(page.getByText(/mistakes won.t cost hearts/i)).toBeVisible();

  const solutions = new Map<string, string>();
  const done = page.getByRole("heading", { name: /lesson!|complete!/ });
  for (let step = 0; step < 15 && !(await done.isVisible()); step++) {
    await page.locator("h1").first().waitFor();
    if (await done.isVisible()) break;
    const prompt = (await page.locator("h1").first().textContent()) ?? "";
    const cantListen = page.getByRole("button", { name: "Can't listen now" });
    if (await cantListen.isVisible()) {
      await cantListen.click();
      await page.waitForTimeout(500);
      continue;
    }
    if (prompt.includes("matching pairs")) {
      await solvePairs(page);
    } else {
      const known = solutions.get(prompt);
      await (known ? page.getByRole("radio", { name: known }) : page.getByRole("radio").first()).click();
      await page.getByRole("button", { name: "Check" }).click();
    }
    const next = page.getByRole("button", { name: "Continue" });
    await next.waitFor();
    if (await page.getByText("Correct solution:").isVisible()) {
      solutions.set(prompt, (await page.locator('[role="alert"] p').textContent()) ?? "");
    }
    await next.click();
  }

  await expect(done).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click(); // results
  await page.getByRole("button", { name: "Continue" }).click(); // streak
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: /Learning Japanese/ }).first()).toBeVisible();
});
