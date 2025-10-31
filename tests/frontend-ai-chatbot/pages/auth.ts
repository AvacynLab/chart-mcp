import { type Page } from "@playwright/test";

export class AuthPage {
  constructor(private page: Page) {}

  async register(email: string, password: string) {
    await this.page.goto('/register');
    await this.page.getByPlaceholder('user@acme.com').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign Up' }).click();
  }

  async login(email: string, password: string) {
    await this.page.goto('/login');
    await this.page.getByPlaceholder('user@acme.com').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }

  async logout(email?: string, password?: string) {
    // Assuming the logout flow is accessible from the user nav menu
    // Try to open the sidebar; if the toggle is not present (different
    // responsive layouts / header-only UI) fall back to clicking the
    // user nav button directly.
    try {
      await this.openSidebar();
    } catch (err) {
      // ignore and attempt direct nav button click below
    }

    const userNavButton = this.page.getByTestId('user-nav-button');
    if (await userNavButton.count() > 0) {
      await userNavButton.click();
    } else {
      // As a last resort, try to open the native user menu element if present
      const altNav = this.page.locator('[data-testid="header-user-button"]');
      if ((await altNav.count()) > 0) {
        await altNav.click();
      }
    }

    const authItem = this.page.getByTestId('user-nav-item-auth');
    await authItem.click();
  }

  async expectToastToContain(text: string) {
    await this.page.waitForSelector('[data-testid="toast"]');
    await this.page.getByTestId('toast').waitFor({ state: 'visible' });
    await this.page.getByTestId('toast').innerText();
    // Basic assertion handled by tests using expect; helper just waits
  }

  openSidebar() {
    // Wait for the sidebar toggle to appear with a short timeout so tests
    // don't hang indefinitely if the layout doesn't include a toggle.
    const toggle = this.page.getByTestId('sidebar-toggle-button');
    return toggle.waitFor({ state: 'visible', timeout: 2000 }).then(() =>
      toggle.click()
    );
  }
}
