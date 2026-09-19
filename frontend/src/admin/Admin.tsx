import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, getAdminUnlock, setAdminUnlock } from "../api/client";
import { formatRub, payStatusLabel, payStatusTone, roleLabel, statusLabel, statusTone, txTypeLabel, when } from "../lib/format";

type Me = { id: number; role: string; first_name?: string; is_owner?: boolean };

const canWrite = (role: string) => ["ADMIN", "SUPERADMIN"].includes(role);
const canAdjust = canWrite;
const isOwnerRole = (role: string) => role === "SUPERADMIN";

function Err({ e }: { e: unknown }) {
  if (!e) return null;
  return <div className="err">{(e as ApiError).message || "Ошибка"}</div>;
}

function Period({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="chips">
      {[["today", "Сегодня"], ["7d", "7 дней"], ["30d", "30 дней"], ["all", "Всё"]].map(([k, l]) => (
        <button key={k} className={value === k ? "on" : ""} onClick={() => onChange(k)}>{l}</button>
      ))}
    </div>
  );
}

function Dash({ me }: { me: Me }) {
  const [period, setPeriod] = useState("7d");
  const ov = useQuery({ queryKey: ["adm-ov", period], queryFn: () => api(`/admin/overview?period=${period}`) });
  const pays = useQuery({ queryKey: ["adm-tp-dash"], queryFn: () => api("/admin/trust-pay?status=processing") });
  const orders = useQuery({ queryKey: ["adm-orders-dash"], queryFn: () => api("/admin/orders?limit=5") });
  const o = ov.data || {};
  const pending = pays.data?.items || [];
  return (
    <div className="grid">
      <div className="between">
        <h1 className="h1 display">Дашборд</h1>
        <span className="muted">{me.first_name}</span>
      </div>
      <Period value={period} onChange={setPeriod} />
      <div className="grid catalog-grid">
        {[
          ["Пользователи", o.users, "/admin/users"],
          ["Заказы", o.orders, "/admin/orders"],
          ["Выручка", o.revenue != null ? formatRub(o.revenue) : "—", "/admin/analytics"],
          ["Прибыль", o.profit != null ? formatRub(o.profit) : "—", "/admin/analytics"],
          ["Trust Pay", o.processing_payments ?? o.pending_payments ?? 0, "/admin/trust-pay"],
          ["Зеркала", o.mirrors, "/admin/mirrors"],
        ].map(([t, v, to]) => (
          <Link key={String(t)} to={String(to)} className="panel pad kpi">
            <div className="tiny">{t}</div>
            <div className="h2 display">{v ?? "—"}</div>
          </Link>
        ))}
      </div>
      {pending.length > 0 && (
        <div className="panel pad grid">
          <div className="between">
            <h2 className="h2">Платежи на проверке</h2>
            <Link to="/admin/trust-pay" className="subtle">Все</Link>
          </div>
          {pending.map((p: any) => (
            <Link key={p.id} to="/admin/trust-pay" className="between">
              <div>
                <b>{p.public_id}</b>
                <div className="muted">@{p.username || p.telegram_id} · {when(p.created_at)}</div>
              </div>
              <b className="num">{formatRub(p.total)}</b>
            </Link>
          ))}
        </div>
      )}
      <h2 className="h2">Последние заказы</h2>
      {(orders.data?.items || []).map((ord: any) => (
        <Link key={ord.id} to={`/admin/orders/${ord.public_id}`} className="panel product">
          <div>
            <b>#{ord.public_id}</b>
            <div className="muted">{ord.product?.name} · {ord.user?.first_name || ord.recipient || "—"}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="num">{formatRub(ord.total_price)}</div>
            <span className={`badge ${statusTone(ord.status)}`}>{statusLabel(ord.status)}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}

function Users({ me }: { me: Me }) {
  const [q, setQ] = useState("");
  const users = useQuery({
    queryKey: ["adm-users", q],
    queryFn: () => api(`/admin/users?q=${encodeURIComponent(q)}&limit=50`),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Пользователи</h1>
      <input placeholder="Имя, @username или Telegram ID" value={q} onChange={(e) => setQ(e.target.value)} />
      {(users.data?.items || []).map((u: any) => (
        <Link key={u.id} to={`/admin/users/${u.id}`} className="panel pad grid">
          <div className="between">
            <div>
              <b>{u.first_name || "—"} {u.username ? `@${u.username}` : ""}</b>
              <div className="muted">ID {u.telegram_id} · {roleLabel(u.role)}</div>
            </div>
            <b className="num">{formatRub(u.balance)}</b>
          </div>
          <div className="row">
            {u.is_owner && <span className="badge ok">Владелец</span>}
            {u.is_blocked && <span className="badge bad">Заблокирован</span>}
          </div>
        </Link>
      ))}
      {!(users.data?.items || []).length && <div className="empty">Никого не нашли</div>}
      {me.role === "MANAGER" && <p className="muted">Просмотр. Изменения — у администратора.</p>}
    </div>
  );
}

function UserDetail({ me }: { me: Me }) {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("Корректировка администратора");
  const d = useQuery({ queryKey: ["adm-user", id], queryFn: () => api(`/admin/users/${id}`) });
  const patch = useMutation({
    mutationFn: (body: object) => api(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-user", id] }),
  });
  if (d.isLoading || !d.data) return <div className="skeleton tall" />;
  const u = d.data.user;
  const write = canWrite(me.role);
  const adj = canAdjust(me.role);
  return (
    <div className="grid">
      <button className="btn ghost" onClick={() => nav("/admin/users")}>Назад</button>
      <div className="panel pad grid">
        <div className="between">
          <div>
            <div className="tiny">{roleLabel(u.role)}</div>
            <h1 className="h1 display">{u.first_name || "Пользователь"}</h1>
            <div className="muted">@{u.username || "—"} · Telegram {u.telegram_id}</div>
          </div>
          {u.is_blocked && <span className="badge bad">Заблокирован</span>}
        </div>
        <div className="h2 num">{formatRub(u.balance)}</div>
        <div className="muted">Реферал {u.referral_code} · приглашено {d.data.referrals?.invited ?? 0}</div>
        {write && !u.is_owner && (
          <button className="btn ghost" onClick={() => patch.mutate({ is_blocked: !u.is_blocked })}>
            {u.is_blocked ? "Разблокировать" : "Заблокировать"}
          </button>
        )}
      </div>
      {adj && (
        <div className="panel pad grid">
          <div className="tiny">Изменить баланс</div>
          <input inputMode="decimal" placeholder="Сумма, −500 списать" value={amount} onChange={(e) => setAmount(e.target.value.replace(",", "."))} />
          <input placeholder="Причина" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Err e={patch.error} />
          <button
            className="btn"
            disabled={patch.isPending || !amount}
            onClick={() => patch.mutate({ adjust_amount: amount, adjust_reason: reason })}
          >
            Применить
          </button>
        </div>
      )}
      {isOwnerRole(me.role) && !u.is_owner && u.role !== "SUPERADMIN" && (
        <div className="panel pad grid">
          <div className="tiny">Роль</div>
          <div className="row">
            {["USER", "MANAGER", "ADMIN"].map((r) => (
              <button key={r} className={`btn sm ${u.role === r ? "" : "ghost"}`} onClick={() => patch.mutate({ role: r })}>{roleLabel(r)}</button>
            ))}
          </div>
        </div>
      )}
      <h2 className="h2">Trust Pay</h2>
      {(d.data.payments || []).map((p: any) => (
        <Link key={p.public_id} to="/admin/trust-pay" className="panel between pad">
          <div>
            <b>{p.public_id}</b>
            <div className="muted">{when(p.created_at)}</div>
          </div>
          <span className={`badge ${payStatusTone(p.status)}`}>{payStatusLabel(p.status)}</span>
        </Link>
      ))}
      <h2 className="h2">Заказы</h2>
      {(d.data.orders || []).map((ord: any) => (
        <Link key={ord.id} to={`/admin/orders/${ord.public_id}`} className="panel between pad">
          <div>
            <b>#{ord.public_id}</b>
            <div className="muted">{ord.product?.name} · {ord.quantity}</div>
          </div>
          <span className={`badge ${statusTone(ord.status)}`}>{statusLabel(ord.status)}</span>
        </Link>
      ))}
      <h2 className="h2">Транзакции</h2>
      {(d.data.transactions || []).map((t: any) => (
        <div key={t.id} className="panel between pad">
          <div>
            <b>{txTypeLabel(t.type)}</b>
            <div className="muted">{t.description} · {when(t.created_at)}</div>
          </div>
          <b className="num">{Number(t.amount) > 0 ? "+" : ""}{formatRub(t.amount)}</b>
        </div>
      ))}
    </div>
  );
}

function Staff({ me }: { me: Me }) {
  const qc = useQueryClient();
  const [staffTg, setStaffTg] = useState("");
  const [staffUser, setStaffUser] = useState("");
  const [staffRole, setStaffRole] = useState("ADMIN");
  const staff = useQuery({ queryKey: ["adm-staff"], queryFn: () => api("/admin/staff") });
  const addStaff = useMutation({
    mutationFn: () => {
      const body: Record<string, string | number> = { role: staffRole };
      const tid = staffTg.replace(/\D/g, "");
      if (tid) body.telegram_id = Number(tid);
      const name = staffUser.replace(/^@/, "").trim();
      if (name) body.username = name;
      return api("/admin/staff", { method: "POST", body: JSON.stringify(body) });
    },
    onSuccess: () => {
      setStaffTg("");
      setStaffUser("");
      qc.invalidateQueries({ queryKey: ["adm-staff"] });
    },
  });
  const dropStaff = useMutation({
    mutationFn: (uid: number) => api(`/admin/staff/${uid}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-staff"] }),
  });
  const owner = isOwnerRole(me.role);
  return (
    <div className="grid">
      <h1 className="h1 display">Команда</h1>
      <p className="muted">Владелец — Telegram ID 8565986003. Назначает администраторов только он.</p>
      {owner && (
        <div className="panel pad grid">
          <div className="tiny">Новый администратор</div>
          <input inputMode="numeric" placeholder="Telegram ID" value={staffTg} onChange={(e) => setStaffTg(e.target.value)} />
          <input placeholder="@username, если уже заходил" value={staffUser} onChange={(e) => setStaffUser(e.target.value)} />
          <div className="chips">
            <button className={staffRole === "ADMIN" ? "on" : ""} onClick={() => setStaffRole("ADMIN")}>Администратор</button>
            <button className={staffRole === "MANAGER" ? "on" : ""} onClick={() => setStaffRole("MANAGER")}>Менеджер</button>
          </div>
          <Err e={addStaff.error} />
          <button className="btn block" disabled={addStaff.isPending || (!staffTg.trim() && !staffUser.trim())} onClick={() => addStaff.mutate()}>Добавить</button>
        </div>
      )}
      {(staff.data?.items || []).map((u: any) => (
        <div key={u.id} className="panel pad grid">
          <div className="between">
            <Link to={`/admin/users/${u.id}`}>
              <b>{u.first_name || "—"} {u.username ? `@${u.username}` : ""}</b>
              <div className="muted">Telegram ID {u.telegram_id}</div>
            </Link>
            <span className={`badge ${u.is_owner || u.role === "SUPERADMIN" ? "ok" : ""}`}>{u.is_owner ? "Владелец" : roleLabel(u.role)}</span>
          </div>
          {owner && !u.is_owner && u.role !== "SUPERADMIN" && (
            <button className="btn ghost sm" onClick={() => dropStaff.mutate(u.id)}>Снять права</button>
          )}
        </div>
      ))}
      <Err e={dropStaff.error} />
    </div>
  );
}

function TrustPayAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const [filter, setFilter] = useState("processing");
  const pays = useQuery({
    queryKey: ["adm-tp", filter],
    queryFn: () => api(`/admin/trust-pay${filter === "all" ? "" : `?status=${filter}`}`),
  });
  const confirmPay = useMutation({
    mutationFn: (pid: number | string) => api(`/admin/trust-pay/${pid}/confirm`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-tp"] }),
  });
  const failPay = useMutation({
    mutationFn: (pid: number | string) => api(`/admin/trust-pay/${pid}/fail`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-tp"] }),
  });
  const adj = canAdjust(me.role);
  return (
    <div className="grid">
      <h1 className="h1 display">Trust Pay</h1>
      <p className="muted">После «Я оплатил» платёж ждёт вашей проверки. На баланс зачисляется сумма без комиссии.</p>
      <div className="chips">
        {[["processing", "На проверке"], ["pending", "Ожидают"], ["paid", "Оплачены"], ["failed", "Отклонённые"], ["all", "Все"]].map(([k, l]) => (
          <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{l}</button>
        ))}
      </div>
      <Err e={confirmPay.error || failPay.error} />
      {(pays.data?.items || []).map((p: any) => (
        <div key={p.id} className="panel pad grid">
          <div className="between">
            <b>{p.public_id}</b>
            <span className={`badge ${payStatusTone(p.status)}`}>{payStatusLabel(p.status)}</span>
          </div>
          <Link to={`/admin/users/${p.user_id}`} className="muted">
            {p.first_name || "user"} @{p.username || "—"} · tg {p.telegram_id}
          </Link>
          <div>
            <div className="between"><span className="muted">К зачислению</span><b className="num">{formatRub(p.amount)}</b></div>
            <div className="between"><span className="muted">Комиссия</span><span className="num">{formatRub(p.fee)}</span></div>
            <div className="between"><span>Перевод</span><strong className="num">{formatRub(p.total)}</strong></div>
          </div>
          <div className="muted">{when(p.created_at)}{p.paid_at ? ` · подтверждён ${when(p.paid_at)}` : ""}</div>
          {adj && (p.status === "pending" || p.status === "processing") && (
            <div className="row">
              <button className="btn" disabled={confirmPay.isPending} onClick={() => confirmPay.mutate(p.id)}>Подтвердить</button>
              <button className="btn ghost" disabled={failPay.isPending} onClick={() => failPay.mutate(p.id)}>Отклонить</button>
            </div>
          )}
        </div>
      ))}
      {!(pays.data?.items || []).length && <div className="empty">Платежей в этом статусе нет</div>}
    </div>
  );
}

function OrdersAdmin({ me }: { me: Me }) {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const orders = useQuery({
    queryKey: ["adm-orders", status, q],
    queryFn: () => api(`/admin/orders?limit=40${status ? `&status=${status}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Заказы</h1>
      <input placeholder="Номер заказа или получатель" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="chips">
        {[["", "Все"], ["APPROVED", "Одобрены"], ["COMPLETED", "Выполнены"], ["REFUNDED", "Возврат"], ["FAILED", "Ошибка"]].map(([k, l]) => (
          <button key={k || "all"} className={status === k ? "on" : ""} onClick={() => setStatus(k)}>{l}</button>
        ))}
      </div>
      {(orders.data?.items || []).map((ord: any) => (
        <Link key={ord.id} to={`/admin/orders/${ord.public_id}`} className="panel product">
          <div>
            <b>#{ord.public_id}</b>
            <div className="muted">{ord.product?.name} · {ord.user?.first_name || ord.recipient || "—"}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="num">{formatRub(ord.total_price)}</div>
            <span className={`badge ${statusTone(ord.status)}`}>{statusLabel(ord.status)}</span>
          </div>
        </Link>
      ))}
      {me && !(orders.data?.items || []).length && <div className="empty">Заказов нет</div>}
    </div>
  );
}

function OrderDetail({ me }: { me: Me }) {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const d = useQuery({ queryKey: ["adm-order", id], queryFn: () => api(`/admin/orders/${id}`) });
  const refund = useMutation({
    mutationFn: () => api(`/admin/orders/${d.data?.id}/refund`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-order", id] }),
  });
  const patch = useMutation({
    mutationFn: (status: string) => api(`/admin/orders/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-order", id] }),
  });
  if (d.isLoading || !d.data) return <div className="skeleton tall" />;
  const o = d.data;
  const write = canWrite(me.role);
  const next =
    o.status === "APPROVED" ? "COMPLETED" :
    o.status === "PENDING" ? "CANCELLED" : "";
  return (
    <div className="grid">
      <button className="btn ghost" onClick={() => nav("/admin/orders")}>Назад</button>
      <div className="panel pad grid">
        <div className="between">
          <h1 className="h2 display">#{o.public_id}</h1>
          <span className={`badge ${statusTone(o.status)}`}>{statusLabel(o.status)}</span>
        </div>
        <div>{o.product?.name} × {o.quantity}</div>
        <div className="h2 num">{formatRub(o.total_price)}</div>
        <div className="muted">Получатель {o.recipient || "—"} · {when(o.created_at)}</div>
        {o.user && (
          <Link to={`/admin/users/${o.user.id}`} className="muted">
            {o.user.first_name} @{o.user.username || "—"} · tg {o.user.telegram_id}
          </Link>
        )}
        <div className="muted">Себестоимость {formatRub(o.provider_cost)} · прибыль {formatRub(o.profit)}</div>
      </div>
      <Err e={refund.error || patch.error} />
      {write && (
        <div className="row">
          {["APPROVED", "COMPLETED", "PROCESSING", "FAILED"].includes(o.status) && (
            <button className="btn ghost" disabled={refund.isPending} onClick={() => refund.mutate()}>Возврат</button>
          )}
          {next && <button className="btn" disabled={patch.isPending} onClick={() => patch.mutate(next)}>{next === "COMPLETED" ? "Отметить выполненным" : "Отменить"}</button>}
        </div>
      )}
      <h2 className="h2">Журнал</h2>
      {(o.logs || []).map((l: any) => (
        <div key={l.id} className="panel pad">
          <b>{l.action}</b>
          <div className="muted">{when(l.created_at)}</div>
        </div>
      ))}
      {!(o.logs || []).length && <div className="muted">Записей журнала нет</div>}
    </div>
  );
}

function ProductsAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const products = useQuery({ queryKey: ["adm-products"], queryFn: () => api("/admin/products") });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: object }) => api(`/admin/products/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-products"] }),
  });
  const write = canWrite(me.role);
  return (
    <div className="grid">
      <h1 className="h1 display">Товары</h1>
      {(products.data?.items || []).map((p: any) => (
        <div key={p.id} className="panel pad grid">
          <div className="between">
            <div>
              <b>{p.name}</b>
              <div className="muted">{p.category} · {p.kind} · от {p.min_quantity}</div>
            </div>
            <span className={`badge ${p.enabled ? "ok" : "bad"}`}>{p.enabled ? "Вкл" : "Выкл"}</span>
          </div>
          <div className="num">{formatRub(p.fallback_unit_price)}</div>
          {write && (
            <button className="btn ghost sm" onClick={() => patch.mutate({ id: p.id, body: { enabled: !p.enabled } })}>
              {p.enabled ? "Выключить" : "Включить"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function MirrorsAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const [mirror, setMirror] = useState({ name: "Aurora", slug: "aurora", markup_percent: "10", description: "Зеркало Aurora" });
  const mirrors = useQuery({ queryKey: ["adm-mirrors"], queryFn: () => api("/admin/mirrors") });
  const createMirror = useMutation({
    mutationFn: () => api("/admin/mirrors", { method: "POST", body: JSON.stringify(mirror) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-mirrors"] }),
  });
  const patch = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) => api(`/admin/mirrors/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-mirrors"] }),
  });
  const write = canWrite(me.role);
  return (
    <div className="grid">
      <h1 className="h1 display">Зеркала</h1>
      {write && (
        <div className="panel grid pad">
          <b>Создать зеркало</b>
          <input value={mirror.name} onChange={(e) => setMirror({ ...mirror, name: e.target.value })} placeholder="Название" />
          <input value={mirror.slug} onChange={(e) => setMirror({ ...mirror, slug: e.target.value })} placeholder="slug" />
          <input value={mirror.markup_percent} onChange={(e) => setMirror({ ...mirror, markup_percent: e.target.value })} placeholder="Наценка %" />
          <input value={mirror.description} onChange={(e) => setMirror({ ...mirror, description: e.target.value })} placeholder="Описание" />
          <div className="panel pad">
            <div className="tiny">Preview</div>
            <b>{mirror.name}</b>
            <div className="muted">{mirror.description} · +{mirror.markup_percent}%</div>
          </div>
          <Err e={createMirror.error} />
          <button className="btn" onClick={() => createMirror.mutate()}>Создать</button>
        </div>
      )}
      {(mirrors.data?.items || []).map((m: any) => (
        <div key={m.id} className="panel pad grid">
          <div className="between">
            <div>
              <b>{m.name}</b>
              <div className="muted">/{m.slug} · {m.orders} заказов</div>
            </div>
            <span className={`badge ${m.enabled ? "ok" : "bad"}`}>{m.enabled ? "Активно" : "Выкл"}</span>
          </div>
          <div className="num">{formatRub(m.revenue)}</div>
          {write && (
            <button className="btn ghost sm" onClick={() => patch.mutate({ id: m.id, enabled: !m.enabled })}>
              {m.enabled ? "Выключить" : "Включить"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function TransactionsAdmin() {
  const [type, setType] = useState("");
  const txs = useQuery({
    queryKey: ["adm-tx", type],
    queryFn: () => api(`/admin/transactions?limit=40${type ? `&type=${type}` : ""}`),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Транзакции</h1>
      <div className="chips">
        {[["", "Все"], ["DEPOSIT", "Пополнения"], ["PURCHASE", "Покупки"], ["REFUND", "Возвраты"], ["ADMIN_ADJUSTMENT", "Корректировки"]].map(([k, l]) => (
          <button key={k || "all"} className={type === k ? "on" : ""} onClick={() => setType(k)}>{l}</button>
        ))}
      </div>
      {(txs.data?.items || []).map((t: any) => (
        <Link key={t.id} to={`/admin/users/${t.user_id}`} className="panel between pad">
          <div>
            <b>{txTypeLabel(t.type)}</b>
            <div className="muted">{t.first_name || t.username || t.user_id} · {t.description} · {when(t.created_at)}</div>
          </div>
          <b className="num">{Number(t.amount) > 0 ? "+" : ""}{formatRub(t.amount)}</b>
        </Link>
      ))}
      {!(txs.data?.items || []).length && <div className="empty">Транзакций нет</div>}
    </div>
  );
}

function AnalyticsAdmin() {
  const [period, setPeriod] = useState("7d");
  const analytics = useQuery({ queryKey: ["adm-an", period], queryFn: () => api(`/admin/analytics?period=${period}`) });
  const series = analytics.data?.series || [];
  const max = Math.max(1, ...series.map((s: any) => Number(s.revenue)));
  return (
    <div className="grid">
      <h1 className="h1 display">Аналитика</h1>
      <Period value={period} onChange={setPeriod} />
      <div className="panel pad">
        <div className="tiny">Выручка</div>
        <div className="chart-bar">
          {series.map((s: any) => (
            <span key={s.day} style={{ height: `${(Number(s.revenue) / max) * 100}%` }} title={`${s.day}: ${formatRub(s.revenue)}`} />
          ))}
        </div>
      </div>
      {series.map((s: any) => (
        <div key={s.day} className="panel between pad">
          <div>
            <b>{s.day}</b>
            <div className="muted">{s.orders} заказов</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="num">{formatRub(s.revenue)}</div>
            <div className="muted">прибыль {formatRub(s.profit)}</div>
          </div>
        </div>
      ))}
      {!series.length && <div className="empty">Нет данных за период</div>}
    </div>
  );
}

function AuditAdmin() {
  const audit = useQuery({ queryKey: ["adm-audit"], queryFn: () => api("/admin/audit") });
  return (
    <div className="grid">
      <h1 className="h1 display">Журнал</h1>
      {(audit.data?.items || []).map((a: any) => (
        <div key={a.id} className="panel pad">
          <b>{a.action}</b>
          <div className="muted">{a.entity} {a.entity_id || ""} · актор {a.actor_id} · {when(a.created_at)}</div>
        </div>
      ))}
    </div>
  );
}

function SettingsAdmin() {
  const settings = useQuery({ queryKey: ["adm-set"], queryFn: () => api("/admin/settings") });
  const labels: Record<string, string> = {
    demo_mode: "DEMO режим",
    referral_enabled: "Рефералы",
    referral_percent: "Реферал %",
    mirrors_enabled: "Зеркала",
    tgstars_enabled: "TGStars live",
    payments_enabled: "Платежи",
    trust_pay_fee_percent: "Комиссия Trust Pay %",
    trust_pay_min_amount: "Мин. пополнение",
    owner_telegram_id: "Telegram ID владельца",
  };
  return (
    <div className="grid">
      <h1 className="h1 display">Настройки</h1>
      <div className="panel pad">
        {Object.entries(settings.data || {}).map(([k, v]) => (
          <div key={k} className="between" style={{ padding: "8px 0" }}>
            <span>{labels[k] || k}</span>
            <b>{String(v)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

function PromosAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const write = canWrite(me.role);
  const promos = useQuery({ queryKey: ["adm-promos"], queryFn: () => api("/admin/promos") });
  const products = useQuery({ queryKey: ["adm-products"], queryFn: () => api("/admin/products") });
  const [form, setForm] = useState({
    code: "",
    kind: "discount",
    amount_type: "percent",
    amount: "10",
    product_id: "",
    max_uses: "",
    per_user: "1",
    min_order: "",
    expires_at: "",
    note: "",
  });
  const create = useMutation({
    mutationFn: () =>
      api("/admin/promos", {
        method: "POST",
        body: JSON.stringify({
          code: form.code || undefined,
          kind: form.kind,
          amount_type: form.kind === "balance" ? "fixed" : form.amount_type,
          amount: form.amount,
          product_id: form.kind === "product" && form.product_id ? Number(form.product_id) : undefined,
          max_uses: form.max_uses ? Number(form.max_uses) : undefined,
          per_user: Number(form.per_user || 1),
          min_order: form.min_order || "0",
          expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : undefined,
          note: form.note,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["adm-promos"] });
      setForm({ ...form, code: "", note: "" });
    },
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: object }) =>
      api(`/admin/promos/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-promos"] }),
  });
  const kindLabel: Record<string, string> = { balance: "Баланс", discount: "Скидка", product: "Товар" };
  return (
    <div className="grid">
      <h1 className="h1 display">Промокоды</h1>
      {write && (
        <div className="panel pad grid">
          <div className="tiny">Новый код</div>
          <div className="chips">
            {[["balance", "На баланс"], ["discount", "Скидка"], ["product", "На товар"]].map(([k, l]) => (
              <button key={k} className={form.kind === k ? "on" : ""} onClick={() => setForm({ ...form, kind: k, amount_type: k === "balance" ? "fixed" : form.amount_type })}>{l}</button>
            ))}
          </div>
          <input placeholder="Код (пусто — сгенерируем)" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          {form.kind !== "balance" && (
            <div className="chips">
              <button className={form.amount_type === "percent" ? "on" : ""} onClick={() => setForm({ ...form, amount_type: "percent" })}>Проценты</button>
              <button className={form.amount_type === "fixed" ? "on" : ""} onClick={() => setForm({ ...form, amount_type: "fixed" })}>Сумма ₽</button>
            </div>
          )}
          <input inputMode="decimal" placeholder={form.amount_type === "percent" ? "Процент, например 15" : "Сумма ₽"} value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
          {form.kind === "product" && (
            <select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
              <option value="">Товар</option>
              {(products.data?.items || []).map((p: any) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
          <div className="filter-price">
            <label>Лимит использований<input inputMode="numeric" placeholder="без лимита" value={form.max_uses} onChange={(e) => setForm({ ...form, max_uses: e.target.value })} /></label>
            <label>На человека<input inputMode="numeric" value={form.per_user} onChange={(e) => setForm({ ...form, per_user: e.target.value })} /></label>
          </div>
          {form.kind !== "balance" && (
            <input inputMode="decimal" placeholder="Мин. сумма заказа ₽" value={form.min_order} onChange={(e) => setForm({ ...form, min_order: e.target.value })} />
          )}
          <label className="tiny">Срок до
            <input type="datetime-local" value={form.expires_at} onChange={(e) => setForm({ ...form, expires_at: e.target.value })} />
          </label>
          <input placeholder="Заметка" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
          <Err e={create.error} />
          <button className="btn block" disabled={create.isPending} onClick={() => create.mutate()}>Создать промокод</button>
        </div>
      )}
      {(promos.data?.items || []).map((p: any) => (
        <div key={p.id} className="panel pad grid">
          <div className="between">
            <div>
              <b className="mono">{p.code}</b>
              <div className="muted">{kindLabel[p.kind] || p.kind} · {p.amount_type === "percent" ? `${Number(p.amount)}%` : formatRub(p.amount)}{p.product_name ? ` · ${p.product_name}` : ""}</div>
            </div>
            <span className={`badge ${p.enabled ? "ok" : "bad"}`}>{p.enabled ? "Активен" : "Выкл"}</span>
          </div>
          <div className="muted">Использований {p.uses_count}{p.max_uses ? ` / ${p.max_uses}` : ""} · на человека {p.per_user}{p.expires_at ? ` · до ${when(p.expires_at)}` : ""}</div>
          {p.note ? <div className="muted">{p.note}</div> : null}
          {write && (
            <div className="row">
              <button className="btn ghost sm" onClick={() => navigator.clipboard.writeText(p.code)}>Копировать</button>
              <button className="btn ghost sm" disabled={patch.isPending} onClick={() => patch.mutate({ id: p.id, body: { enabled: !p.enabled } })}>
                {p.enabled ? "Отключить" : "Включить"}
              </button>
            </div>
          )}
        </div>
      ))}
      {!(promos.data?.items || []).length && <div className="empty">Промокодов пока нет</div>}
    </div>
  );
}

function PricingAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const write = canWrite(me.role);
  const pricing = useQuery({ queryKey: ["adm-pricing"], queryFn: () => api("/admin/pricing") });
  const [globalPct, setGlobalPct] = useState("");
  const [cats, setCats] = useState<Record<string, string>>({});
  const [sale, setSale] = useState({ name: "", percent: "10", categories: "all", expires_at: "" });
  const [newPass, setNewPass] = useState("");
  useEffect(() => {
    if (!pricing.data) return;
    setGlobalPct(String(Number(pricing.data.global_percent)));
    const next: Record<string, string> = {};
    Object.entries(pricing.data.categories || {}).forEach(([k, v]) => {
      next[k] = v == null ? "" : String(Number(v));
    });
    setCats(next);
  }, [pricing.data]);
  const save = useMutation({
    mutationFn: () =>
      api("/admin/pricing", {
        method: "PUT",
        body: JSON.stringify({
          global_percent: globalPct || "0",
          categories: Object.fromEntries(Object.entries(cats).map(([k, v]) => [k, v === "" ? null : Number(v)])),
          admin_password: newPass || undefined,
        }),
      }),
    onSuccess: () => {
      setNewPass("");
      qc.invalidateQueries({ queryKey: ["adm-pricing"] });
      qc.invalidateQueries({ queryKey: ["catalog"] });
    },
  });
  const createSale = useMutation({
    mutationFn: () =>
      api("/admin/sales", {
        method: "POST",
        body: JSON.stringify({
          name: sale.name,
          percent: sale.percent,
          categories: sale.categories,
          enabled: true,
          expires_at: sale.expires_at ? new Date(sale.expires_at).toISOString() : undefined,
        }),
      }),
    onSuccess: () => {
      setSale({ name: "", percent: "10", categories: "all", expires_at: "" });
      qc.invalidateQueries({ queryKey: ["adm-pricing"] });
      qc.invalidateQueries({ queryKey: ["catalog"] });
    },
  });
  const patchSale = useMutation({
    mutationFn: ({ id, body }: { id: number; body: object }) =>
      api(`/admin/sales/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["adm-pricing"] });
      qc.invalidateQueries({ queryKey: ["catalog"] });
    },
  });
  const labels: Record<string, string> = { stars: "Stars", premium: "Premium", nft: "NFT", username: "Username", number: "Номера" };
  return (
    <div className="grid">
      <h1 className="h1 display">Цены и акции</h1>
      <p className="muted lead">Процент к цене API: плюс — наценка, минус — скидка на весь магазин. Акция даёт дополнительную скидку сверху.</p>
      <div className="panel pad grid">
        <div className="tiny">Наценка к API</div>
        <label className="tiny">Все товары, %
          <input inputMode="decimal" value={globalPct} onChange={(e) => setGlobalPct(e.target.value)} placeholder="0" />
        </label>
        <div className="filter-price">
          {Object.keys(labels).map((k) => (
            <label key={k} className="tiny">{labels[k]}, %
              <input inputMode="decimal" placeholder="как все" value={cats[k] ?? ""} onChange={(e) => setCats({ ...cats, [k]: e.target.value })} />
            </label>
          ))}
        </div>
        {write && me.role === "SUPERADMIN" && (
          <label className="tiny">Новый пароль админки
            <input type="password" autoComplete="new-password" value={newPass} onChange={(e) => setNewPass(e.target.value)} placeholder="оставить как есть" />
          </label>
        )}
        <Err e={save.error} />
        {write && <button className="btn block" disabled={save.isPending} onClick={() => save.mutate()}>Сохранить цены</button>}
      </div>
      {write && (
        <div className="panel pad grid">
          <div className="tiny">Новая акция</div>
          <input placeholder="Название, например −20% на Stars" value={sale.name} onChange={(e) => setSale({ ...sale, name: e.target.value })} />
          <input inputMode="decimal" placeholder="Скидка %" value={sale.percent} onChange={(e) => setSale({ ...sale, percent: e.target.value })} />
          <div className="chips">
            {[["all", "Все"], ["stars", "Stars"], ["premium", "Premium"], ["nft", "NFT"], ["username", "Username"], ["number", "Номера"]].map(([k, l]) => (
              <button key={k} className={sale.categories === k ? "on" : ""} onClick={() => setSale({ ...sale, categories: k })}>{l}</button>
            ))}
          </div>
          <label className="tiny">До
            <input type="datetime-local" value={sale.expires_at} onChange={(e) => setSale({ ...sale, expires_at: e.target.value })} />
          </label>
          <Err e={createSale.error} />
          <button className="btn block" disabled={createSale.isPending || !sale.name.trim()} onClick={() => createSale.mutate()}>Запустить акцию</button>
        </div>
      )}
      {(pricing.data?.sales || []).map((s: any) => (
        <div key={s.id} className="panel pad grid">
          <div className="between">
            <div>
              <b>{s.name}</b>
              <div className="muted">−{Number(s.percent)}% · {s.categories === "all" ? "все категории" : s.categories}{s.expires_at ? ` · до ${when(s.expires_at)}` : ""}</div>
            </div>
            <span className={`badge ${s.enabled ? "ok" : "bad"}`}>{s.enabled ? "Активна" : "Выкл"}</span>
          </div>
          {write && (
            <button className="btn ghost sm" disabled={patchSale.isPending} onClick={() => patchSale.mutate({ id: s.id, body: { enabled: !s.enabled } })}>
              {s.enabled ? "Остановить" : "Включить"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function AdminLock({ onUnlock }: { onUnlock: () => void }) {
  const [password, setPassword] = useState("");
  const unlock = useMutation({
    mutationFn: () => api("/admin/unlock", { method: "POST", body: JSON.stringify({ password }) }),
    onSuccess: (d: any) => {
      setAdminUnlock(d.token);
      onUnlock();
    },
  });
  return (
    <div className="grid admin-lock">
      <div className="panel pad grid">
        <div className="tiny">Админ-панель</div>
        <h1 className="h1 display">Пароль</h1>
        <p className="muted">Сначала введите пароль администратора. Без него панель недоступна.</p>
        <input
          type="password"
          autoComplete="current-password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && password && unlock.mutate()}
        />
        <Err e={unlock.error} />
        <button className="btn block" disabled={!password || unlock.isPending} onClick={() => unlock.mutate()}>Войти</button>
      </div>
    </div>
  );
}

export function AdminApp({ me }: { me: Me }) {
  const [unlocked, setUnlocked] = useState(Boolean(getAdminUnlock()));
  const status = useQuery({
    queryKey: ["admin-unlock"],
    queryFn: () => api("/admin/unlock"),
    retry: false,
  });
  useEffect(() => {
    if (status.data?.unlocked) setUnlocked(true);
    if (status.data && status.data.unlocked === false) setUnlocked(false);
  }, [status.data]);
  useEffect(() => {
    const lock = () => setUnlocked(false);
    window.addEventListener("lumina-admin-lock", lock);
    return () => window.removeEventListener("lumina-admin-lock", lock);
  }, []);
  if (status.isLoading && !unlocked) return <div className="skeleton" />;
  if (!unlocked) return <AdminLock onUnlock={() => { setUnlocked(true); status.refetch(); }} />;
  return (
    <Routes>
      <Route index element={<Dash me={me} />} />
      <Route path="users" element={<Users me={me} />} />
      <Route path="users/:id" element={<UserDetail me={me} />} />
      <Route path="staff" element={<Staff me={me} />} />
      <Route path="trust-pay" element={<TrustPayAdmin me={me} />} />
      <Route path="orders" element={<OrdersAdmin me={me} />} />
      <Route path="orders/:id" element={<OrderDetail me={me} />} />
      <Route path="products" element={<ProductsAdmin me={me} />} />
      <Route path="promos" element={<PromosAdmin me={me} />} />
      <Route path="pricing" element={<PricingAdmin me={me} />} />
      <Route path="mirrors" element={<MirrorsAdmin me={me} />} />
      <Route path="transactions" element={<TransactionsAdmin />} />
      <Route path="analytics" element={<AnalyticsAdmin />} />
      <Route path="audit" element={["ADMIN", "SUPERADMIN"].includes(me.role) ? <AuditAdmin /> : <Navigate to="/admin" />} />
      <Route path="settings" element={me.role === "SUPERADMIN" ? <SettingsAdmin /> : <Navigate to="/admin" />} />
      <Route path="*" element={<Navigate to="/admin" />} />
    </Routes>
  );
}