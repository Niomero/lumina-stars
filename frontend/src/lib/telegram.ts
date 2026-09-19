export function getWebApp() {
  return window.Telegram?.WebApp;
}

export function isTelegramWebApp() {
  const tg = getWebApp();
  if (!tg) return false;
  if (typeof tg.initData === "string" && tg.initData.length > 8) return true;
  if (tg.initDataUnsafe?.user?.id) return true;
  return false;
}

export function bootTelegram() {
  const tg = getWebApp();
  if (!tg) return null;
  tg.ready?.();
  tg.expand?.();
  tg.setHeaderColor?.("#0b0a09");
  tg.setBackgroundColor?.("#0b0a09");
  return tg;
}

export function haptic(type: "light" | "medium" | "success" | "error" = "light") {
  const h = getWebApp()?.HapticFeedback;
  if (!h) return;
  if (type === "success") h.notificationOccurred?.("success");
  else if (type === "error") h.notificationOccurred?.("error");
  else h.impactOccurred?.(type);
}

export function openExternal(url: string) {
  if (!url) return;
  const tg = getWebApp();
  if (tg?.openLink) {
    tg.openLink(url);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

export function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

export function prefersReducedMotion() {
  return Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
}

export async function waitForTelegram(ms = 700) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    bootTelegram();
    if (isTelegramWebApp()) return true;
    await sleep(50);
  }
  bootTelegram();
  return isTelegramWebApp();
}

export function canPreviewDemo(demoEnabled: boolean, appEnv?: string | null) {
  if (!demoEnabled) return false;
  return (appEnv || "").toLowerCase() !== "production";
}
