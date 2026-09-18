export function getWebApp() {
  return window.Telegram?.WebApp;
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
