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

export function payStatusLabel(status: string) {
  const map: Record<string, string> = {
    pending: "Ожидает оплаты",
    processing: "Ожидает проверки",
    paid: "Успешно",
    failed: "Отклонён",
    cancelled: "Отменён",
    expired: "Истёк",
  };
  return map[status] || status;
}

export function payStatusTone(status: string) {
  if (status === "paid") return "ok";
  if (["failed", "cancelled", "expired"].includes(status)) return "bad";
  return "warn";
}

export function roleLabel(role: string) {
  const map: Record<string, string> = {
    SUPERADMIN: "Суперадмин",
    ADMIN: "Администратор",
    MANAGER: "Менеджер",
    MIRROR_OWNER: "Владелец зеркала",
    USER: "Пользователь",
  };
  return map[role] || role;
}
