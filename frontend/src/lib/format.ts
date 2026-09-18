export function formatRub(value: string | number | null | undefined) {
  const n = Number(value || 0);
  return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 2 }).format(n);
}

export function statusLabel(status: string) {
  const map: Record<string, string> = {
    PENDING: "Создан",
    PROCESSING: "В обработке",
    APPROVED: "Одобрен и передан",
    COMPLETED: "Выполнен",
    FAILED: "Ошибка",
    CANCELLED: "Отменён",
    REFUNDED: "Возврат",
  };
  return map[status] || status;
}

export function statusTone(status: string) {
  if (["APPROVED", "COMPLETED"].includes(status)) return "ok";
  if (["FAILED", "CANCELLED"].includes(status)) return "bad";
  return "warn";
}
