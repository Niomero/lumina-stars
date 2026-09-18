export function getWebApp() {
  return window.Telegram?.WebApp;
}

export function bootTelegram() {
  const tg = getWebApp();
  if (!tg) return null;
  tg.ready?.();
  tg.expand?.();
  tg.setHeaderColor?.("#07070c");
  tg.setBackgroundColor?.("#07070c");
  return tg;
}

export function haptic(type: "light" | "medium" | "success" | "error" = "light") {
  const h = getWebApp()?.HapticFeedback;
  if (!h) return;
  if (type === "success") h.notificationOccurred?.("success");
  else if (type === "error") h.notificationOccurred?.("error");
  else h.impactOccurred?.(type);
}
