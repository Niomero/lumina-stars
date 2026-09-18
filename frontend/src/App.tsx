import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Home as HomeIcon,
  Store,
  Receipt,
  Wallet,
  UserRound,
  Sparkles,
  Crown,
  Gem,
  Plus,
  Minus,
  Check,
  ChevronRight,
  RefreshCw,
  Shield,
} from "lucide-react";
import { api, ApiError, clearToken, getToken, setToken } from "./api/client";
import { formatRub, statusLabel, statusTone } from "./lib/format";
import { bootTelegram, haptic } from "./lib/telegram";

type Me = {
  id: number;
  first_name?: string;
  username?: string;
  role: string;
  balance: string;
  orders_count: number;
  spent: string;
  referral_code: string;
  photo_url?: string;
};

const isStaff = (role?: string) => ["MANAGER", "ADMIN", "SUPERADMIN", "MIRROR_OWNER"].includes(role || "");

function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["me"],
    enabled,
    queryFn: () => api<Me>("/me"),
  });
}

function Shell({ me, children }: { me: Me; children: React.ReactNode }) {
  const loc = useLocation();
  const nav = [
    { to: "/", icon: HomeIcon, label: "Главная" },
    { to: "/catalog", icon: Store, label: "Каталог" },
    { to: "/orders", icon: Receipt, label: "Заказы" },
    { to: "/balance", icon: Wallet, label: "Баланс" },
    { to: "/profile", icon: UserRound, label: "Профиль" },
  ];
  const admin = loc.pathname.startsWith("/admin");
  return (
    <div className={`app ${admin ? "admin" : ""}`}>
      {admin ? (
        <div className="admin-layout">
          <aside className="sidebar glass">
            <div className="row"><div className="logo-mark">L</div><b className="display">Lumina</b></div>
            {[
              ["/admin", "Дашборд"],
              ["/admin/users", "Пользователи"],
              ["/admin/orders", "Заказы"],
              ["/admin/products", "Товары"],
              ["/admin/mirrors", "Зеркала"],
              ["/admin/analytics", "Аналитика"],
              ["/admin/settings", "Настройки"],
            ].map(([to, label]) => (
              <Link key={to} to={to} className={loc.pathname === to ? "btn block" : "btn ghost block"}>{label}</Link>
            ))}
            <Link to="/" className="btn ghost block">В магазин</Link>
          </aside>
          <div>{children}</div>
        </div>
      ) : (
        children
      )}
      {!admin && (
        <nav className="nav glass">
          {nav.map((n) => {
            const Icon = n.icon;
            const active = n.to === "/" ? loc.pathname === "/" : loc.pathname.startsWith(n.to);
            return (
              <Link key={n.to} to={n.to} className={active ? "active" : ""}>
                <Icon />
                {n.label}
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}

function Home({ me }: { me: Me }) {
  const { data, isLoading } = useQuery({ queryKey: ["catalog"], queryFn: () => api("/catalog") });
  const popular = (data?.items || []).filter((p: any) => p.popular);
  return (
    <div className="grid">
      <div className="between">
        <div>
          <div className="tiny">Добро пожаловать</div>
          <h1 className="h1 display">Привет, {me.first_name || "друг"}</h1>
        </div>
        <div className="logo-mark">L</div>
      </div>
      <div className="glass" style={{ padding: 20 }}>
        <div className="tiny">Баланс</div>
        <div className="between">
          <div className="h1 display">{formatRub(me.balance)}</div>
          <Link to="/balance" className="btn gold">Пополнить</Link>
        </div>
      </div>
      <div className="between"><h2 className="h2 display">Популярное</h2><Link to="/catalog" className="muted">Все</Link></div>
      {isLoading && <div className="skeleton" />}
      <div className="grid catalog-grid">
        {popular.map((p: any) => (
          <Link key={p.id} to={`/product/${p.id}`} className="glass product">
            <div className="icon-blob">{p.kind === "premium" ? <Crown size={20} /> : <Sparkles size={20} />}</div>
            <div style={{ flex: 1 }}>
              <b>{p.name}</b>
              <div className="muted">{formatRub(p.unit_price)} {p.kind === "stars" ? "за звезду" : "за мес."}</div>
            </div>
            <ChevronRight size={16} color="#9aa3b5" />
          </Link>
        ))}
      </div>
      <Link to="/catalog" className="btn block">Быстрый заказ</Link>
    </div>
  );
}

function Catalog() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState("popular");
  const [sheet, setSheet] = useState(false);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["catalog", q, category, sort],
    queryFn: () => api(`/catalog?q=${encodeURIComponent(q)}&category=${category}&sort=${sort}`),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Каталог</h1>
      <input placeholder="Что вы ищете?" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="row">
        {["all", "stars", "premium"].map((c) => (
          <button key={c} className={`btn ${category === c ? "" : "ghost"}`} onClick={() => setCategory(c)}>
            {c === "all" ? "Все" : c === "stars" ? "Stars" : "Premium"}
          </button>
        ))}
        <button className="btn ghost" onClick={() => setSheet(true)}>Фильтры</button>
      </div>
      {isLoading && <><div className="skeleton" /><div className="skeleton" /></>}
      {error && <div className="empty err">Не удалось загрузить данные<br /><button className="btn ghost" onClick={() => refetch()}>Повторить</button></div>}
      {(data?.items || []).map((p: any) => (
        <Link key={p.id} to={`/product/${p.id}`} className="glass product">
          <div className="icon-blob">{p.kind === "premium" ? <Gem size={20} /> : <Sparkles size={20} />}</div>
          <div style={{ flex: 1 }}>
            <b>{p.name}</b>
            <div className="muted">{p.description}</div>
          </div>
          <b>{formatRub(p.preview_total)}</b>
        </Link>
      ))}
      {sheet && (
        <div className="sheet" onClick={() => setSheet(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2">Сортировка</h2>
            {[
              ["popular", "По популярности"],
              ["new", "Новые"],
              ["price_asc", "Цена ↑"],
              ["price_desc", "Цена ↓"],
            ].map(([k, l]) => (
              <button key={k} className={`btn ${sort === k ? "" : "ghost"}`} onClick={() => { setSort(k); setSheet(false); }}>{l}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ProductPage({ me }: { me: Me }) {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [qty, setQty] = useState(100);
  const [recipient, setRecipient] = useState(me.username || "");
  const [confirm, setConfirm] = useState(false);
  const [done, setDone] = useState<any>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["product", id, qty],
    queryFn: () => api(`/products/${id}?quantity=${qty}`),
  });
  useEffect(() => {
    if (data?.kind === "premium") setQty(data.min_quantity);
  }, [data?.kind, data?.min_quantity]);
  const buy = useMutation({
    mutationFn: () =>
      api("/orders", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(id),
          quantity: qty,
          recipient,
          idempotency_key: crypto.randomUUID(),
        }),
      }),
    onSuccess: (order) => {
      haptic("success");
      setConfirm(false);
      setDone(order);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });
  if (isLoading || !data) return <div className="skeleton" />;
  const presets = data.presets || [50, 100, 250, 500, 1000];
  const after = Number(me.balance) - Number(data.total);
  return (
    <div className="grid">
      <button className="btn ghost" onClick={() => nav(-1)}>Назад</button>
      <div className="glass" style={{ padding: 20 }}>
        <div className="icon-blob" style={{ width: 64, height: 64 }}><Sparkles /></div>
        <h1 className="h1 display">{data.name}</h1>
        <p className="muted">{data.description}</p>
        <div className="tiny">Текущая цена</div>
        <div className="h2">{formatRub(data.unit_price)} {data.kind === "stars" ? " / звезда" : " / мес."}</div>
      </div>
      {data.kind === "stars" && (
        <>
          <div className="qty">
            <button onClick={() => setQty(Math.max(data.min_quantity, qty - data.step))}><Minus size={16} /></button>
            <b style={{ fontSize: 28 }} className="display">{qty}</b>
            <button onClick={() => setQty(Math.min(data.max_quantity, qty + data.step))}><Plus size={16} /></button>
          </div>
          <div className="presets">
            {presets.map((p: number) => (
              <button key={p} className={qty === p ? "on" : ""} onClick={() => setQty(p)}>{p}</button>
            ))}
          </div>
        </>
      )}
      <input placeholder="Username получателя без @" value={recipient} onChange={(e) => setRecipient(e.target.value.replace("@", ""))} />
      <div className="glass" style={{ padding: 16 }}>
        <div className="between"><span className="muted">Итог</span><b>{data.quantity} × {formatRub(data.unit_price)}</b></div>
        <div className="between"><span className="muted">К оплате</span><b className="h2">{formatRub(data.total)}</b></div>
        <div className="between"><span className="muted">Баланс</span><span>{formatRub(me.balance)}</span></div>
      </div>
      {buy.error && <div className="err">{(buy.error as ApiError).message}</div>}
      <button className="btn block gold" onClick={() => { haptic("medium"); setConfirm(true); }}>Купить за {formatRub(data.total)}</button>
      {confirm && (
        <div className="sheet" onClick={() => setConfirm(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2 display">Подтвердить заказ?</h2>
            <div>Товар: {data.name}</div>
            <div>Количество: {data.quantity}</div>
            <div>Цена: {formatRub(data.total)}</div>
            <div>Баланс после: {formatRub(after)}</div>
            <div className="row">
              <button className="btn ghost block" onClick={() => setConfirm(false)}>Отмена</button>
              <button className="btn block" disabled={buy.isPending} onClick={() => buy.mutate()}>Подтвердить</button>
            </div>
          </div>
        </div>
      )}
      {done && (
        <div className="sheet">
          <div className="panel grid" style={{ textAlign: "center" }}>
            <div className="success-mark"><Check size={40} /></div>
            <h2 className="h2 display">Заказ одобрен</h2>
            <div className="muted">Заказ передан</div>
            <div>Номер заказа: #{done.public_id}</div>
            <div>Товар: {data.name}</div>
            <div>Количество: {done.quantity}</div>
            <div>Сумма: {formatRub(done.total_price)}</div>
            <Link className="btn block" to={`/orders/${done.public_id}`}>Посмотреть заказ</Link>
          </div>
        </div>
      )}
    </div>
  );
}

function Orders() {
  const { data, isLoading } = useQuery({ queryKey: ["orders"], queryFn: () => api("/orders") });
  if (isLoading) return <div className="skeleton" />;
  const items = data?.items || [];
  if (!items.length) {
    return <div className="empty">У вас пока нет заказов<br /><Link to="/catalog" className="btn" style={{ display: "inline-block", marginTop: 12 }}>Перейти в каталог</Link></div>;
  }
  return (
    <div className="grid">
      <h1 className="h1 display">Заказы</h1>
      {items.map((o: any) => (
        <Link key={o.id} to={`/orders/${o.public_id}`} className="glass product">
          <div>
            <b>#{o.public_id}</b>
            <div className="muted">{o.product?.name} · {o.quantity}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div>{formatRub(o.total_price)}</div>
            <span className={`badge ${statusTone(o.status)}`}>{statusLabel(o.status)}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}

function OrderPage() {
  const { id } = useParams();
  const { data, isLoading } = useQuery({ queryKey: ["order", id], queryFn: () => api(`/orders/${id}`) });
  if (isLoading || !data) return <div className="skeleton" />;
  return (
    <div className="grid">
      <h1 className="h1 display">Заказ #{data.public_id}</h1>
      <div className="glass" style={{ padding: 16 }}>
        <div>{data.product?.name}</div>
        <div className="muted">Количество: {data.quantity}</div>
        <div>Итог: {formatRub(data.total_price)}</div>
        <span className={`badge ${statusTone(data.status)}`}>{statusLabel(data.status)}</span>
      </div>
      <div className="glass" style={{ padding: 16 }}>
        {(data.timeline || []).map((s: any, i: number) => (
          <div key={s.key} className="row" style={{ opacity: s.done ? 1 : 0.4, padding: "8px 0" }}>
            <div className="icon-blob" style={{ width: 28, height: 28, borderRadius: 10 }}>{s.done ? <Check size={14} /> : i + 1}</div>
            <div>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Balance({ me }: { me: Me }) {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["tx"], queryFn: () => api("/transactions") });
  const deposit = useMutation({
    mutationFn: () => api("/balance/deposit", { method: "POST", body: JSON.stringify({ amount: "1000" }) }),
    onSuccess: () => { qc.invalidateQueries(); haptic("success"); },
  });
  return (
    <div className="grid">
      <div className="glass" style={{ padding: 24, textAlign: "center" }}>
        <div className="tiny">Баланс</div>
        <div className="h1 display" style={{ fontSize: 40 }}>{formatRub(me.balance)}</div>
        <button className="btn gold" onClick={() => deposit.mutate()} disabled={deposit.isPending}>Пополнить на 1 000 ₽</button>
        <div className="muted" style={{ marginTop: 8 }}>Демо-пополнение</div>
      </div>
      <h2 className="h2">История операций</h2>
      {(data?.items || []).length === 0 && <div className="empty">История операций пуста</div>}
      {(data?.items || []).map((t: any) => (
        <div key={t.id} className="between glass" style={{ padding: 14 }}>
          <div>
            <b>{t.description}</b>
            <div className="muted">{new Date(t.created_at).toLocaleString("ru")}</div>
          </div>
          <b style={{ color: Number(t.amount) < 0 ? "var(--rose)" : "var(--mint)" }}>
            {Number(t.amount) > 0 ? "+" : ""}{formatRub(t.amount)}
          </b>
        </div>
      ))}
    </div>
  );
}

function Referrals() {
  const { data } = useQuery({ queryKey: ["ref"], queryFn: () => api("/referrals") });
  if (!data) return <div className="skeleton" />;
  return (
    <div className="grid">
      <h1 className="h1 display">Рефералы</h1>
      <div className="glass" style={{ padding: 18 }}>
        <div className="tiny">Ваш код</div>
        <h2 className="h2">{data.code}</h2>
        <div className="muted">Награда {data.percent}% с покупок друзей</div>
        <p style={{ wordBreak: "break-all" }}>{data.link}</p>
        <button className="btn block" onClick={() => navigator.clipboard.writeText(data.link)}>Скопировать ссылку</button>
      </div>
      <div className="row">
        <div className="glass" style={{ padding: 16, flex: 1 }}><div className="tiny">Приглашено</div><b>{data.invited}</b></div>
        <div className="glass" style={{ padding: 16, flex: 1 }}><div className="tiny">Заработано</div><b>{formatRub(data.earned)}</b></div>
      </div>
    </div>
  );
}

function Profile({ me }: { me: Me }) {
  const cards = [
    ["/balance", "Баланс", formatRub(me.balance)],
    ["/orders", "Мои заказы", String(me.orders_count || 0)],
    ["/transactions", "Транзакции", "История"],
    ["/referrals", "Рефералы", me.referral_code],
  ];
  return (
    <div className="grid">
      <div className="glass product">
        <div className="logo-mark">{(me.first_name || "L")[0]}</div>
        <div>
          <h2 className="h2">{me.first_name}</h2>
          <div className="muted">@{me.username || "user"} · {me.role}</div>
        </div>
      </div>
      {cards.map(([to, t, s]) => (
        <Link key={to} to={to} className="glass between" style={{ padding: 16 }}>
          <b>{t}</b><span className="muted">{s}</span>
        </Link>
      ))}
      {isStaff(me.role) && <Link to="/admin" className="btn block"><Shield size={16} /> Админ-панель</Link>}
    </div>
  );
}

function Transactions() {
  const { data } = useQuery({ queryKey: ["tx"], queryFn: () => api("/transactions") });
  return (
    <div className="grid">
      <h1 className="h1 display">Транзакции</h1>
      {(data?.items || []).map((t: any) => (
        <div key={t.id} className="glass between" style={{ padding: 14 }}>
          <div><b>{t.description}</b><div className="muted">{t.type}</div></div>
          <b>{formatRub(t.amount)}</b>
        </div>
      ))}
    </div>
  );
}

function AdminPage({ path }: { path: string }) {
  const qc = useQueryClient();
  const overview = useQuery({ queryKey: ["adm-ov"], queryFn: () => api("/admin/overview?period=7d") });
  const users = useQuery({ queryKey: ["adm-users"], queryFn: () => api("/admin/users"), enabled: path === "users" });
  const orders = useQuery({ queryKey: ["adm-orders"], queryFn: () => api("/admin/orders"), enabled: path === "orders" });
  const products = useQuery({ queryKey: ["adm-products"], queryFn: () => api("/admin/products"), enabled: path === "products" });
  const mirrors = useQuery({ queryKey: ["adm-mirrors"], queryFn: () => api("/admin/mirrors"), enabled: path === "mirrors" });
  const analytics = useQuery({ queryKey: ["adm-an"], queryFn: () => api("/admin/analytics?period=7d"), enabled: path === "analytics" });
  const settings = useQuery({ queryKey: ["adm-set"], queryFn: () => api("/admin/settings"), enabled: path === "settings" });
  const [mirror, setMirror] = useState({ name: "Aurora", slug: "aurora", markup_percent: "10", description: "Зеркало Aurora" });
  const createMirror = useMutation({
    mutationFn: () => api("/admin/mirrors", { method: "POST", body: JSON.stringify(mirror) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-mirrors"] }),
  });
  const refund = useMutation({
    mutationFn: (id: number) => api(`/admin/orders/${id}/refund`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-orders"] }),
  });
  const patchProduct = useMutation({
    mutationFn: ({ id, enabled }: any) => api(`/admin/products/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-products"] }),
  });

  if (path === "users") {
    return (
      <div className="grid">
        <h1 className="h1 display">Пользователи</h1>
        {(users.data?.items || []).map((u: any) => (
          <div key={u.id} className="glass between" style={{ padding: 14 }}>
            <div><b>{u.first_name} @{u.username}</b><div className="muted">{u.role}</div></div>
            <div>{formatRub(u.balance)}</div>
          </div>
        ))}
      </div>
    );
  }
  if (path === "orders") {
    return (
      <div className="grid">
        <h1 className="h1 display">Заказы</h1>
        {(orders.data?.items || []).map((o: any) => (
          <div key={o.id} className="glass between" style={{ padding: 14 }}>
            <div><b>#{o.public_id}</b><div className="muted">{o.product?.name} · {o.recipient}</div></div>
            <div>
              <div>{formatRub(o.total_price)}</div>
              <button className="btn ghost" onClick={() => refund.mutate(o.id)}>Возврат</button>
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (path === "products") {
    return (
      <div className="grid">
        <h1 className="h1 display">Товары</h1>
        {(products.data?.items || []).map((p: any) => (
          <div key={p.id} className="glass between" style={{ padding: 14 }}>
            <div><b>{p.name}</b><div className="muted">{p.category}</div></div>
            <button className="btn ghost" onClick={() => patchProduct.mutate({ id: p.id, enabled: !p.enabled })}>{p.enabled ? "Выкл" : "Вкл"}</button>
          </div>
        ))}
      </div>
    );
  }
  if (path === "mirrors") {
    return (
      <div className="grid">
        <h1 className="h1 display">Зеркала</h1>
        <div className="glass grid" style={{ padding: 16 }}>
          <b>Создать зеркало</b>
          <input value={mirror.name} onChange={(e) => setMirror({ ...mirror, name: e.target.value })} placeholder="Название" />
          <input value={mirror.slug} onChange={(e) => setMirror({ ...mirror, slug: e.target.value })} placeholder="slug" />
          <input value={mirror.markup_percent} onChange={(e) => setMirror({ ...mirror, markup_percent: e.target.value })} placeholder="Наценка %" />
          <div className="glass" style={{ padding: 12, borderColor: "#7eb6ff" }}>
            <div className="tiny">Preview</div>
            <b>{mirror.name}</b>
            <div className="muted">{mirror.description} · +{mirror.markup_percent}%</div>
          </div>
          <button className="btn" onClick={() => createMirror.mutate()}>Создать</button>
        </div>
        {(mirrors.data?.items || []).map((m: any) => (
          <div key={m.id} className="glass between" style={{ padding: 14 }}>
            <div><b>{m.name}</b><div className="muted">/{m.slug} · {m.orders} заказов</div></div>
            <div>{formatRub(m.revenue)}</div>
          </div>
        ))}
      </div>
    );
  }
  if (path === "analytics") {
    const series = analytics.data?.series || [];
    const max = Math.max(1, ...series.map((s: any) => Number(s.revenue)));
    return (
      <div className="grid">
        <h1 className="h1 display">Аналитика</h1>
        <div className="glass" style={{ padding: 16 }}>
          <div className="chart-bar">
            {series.map((s: any) => <span key={s.day} style={{ height: `${(Number(s.revenue) / max) * 100}%` }} title={s.day} />)}
          </div>
        </div>
      </div>
    );
  }
  if (path === "settings") {
    return (
      <div className="grid">
        <h1 className="h1 display">Настройки</h1>
        <div className="glass" style={{ padding: 16 }}>
          {Object.entries(settings.data || {}).map(([k, v]) => (
            <div key={k} className="between" style={{ padding: "8px 0" }}><span>{k}</span><b>{String(v)}</b></div>
          ))}
        </div>
      </div>
    );
  }
  const o = overview.data || {};
  return (
    <div className="grid">
      <h1 className="h1 display">Админка</h1>
      <div className="grid catalog-grid">
        {[
          ["Пользователи", o.users],
          ["Заказы", o.orders],
          ["Выручка", formatRub(o.revenue)],
          ["Прибыль", formatRub(o.profit)],
        ].map(([t, v]) => (
          <div key={String(t)} className="glass" style={{ padding: 16 }}>
            <div className="tiny">{t}</div>
            <div className="h2 display">{v ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [authed, setAuthed] = useState(!!getToken());
  const [error, setError] = useState("");
  const me = useMe(authed);

  useEffect(() => {
    const tg = bootTelegram();
    const run = async () => {
      try {
        if (tg?.initData) {
          const data = await api("/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: tg.initData }) });
          setToken(data.token);
          setAuthed(true);
        } else if (!getToken()) {
          const data = await api("/auth/demo", { method: "POST", body: JSON.stringify({ name: "Lumina" }) });
          setToken(data.token);
          setAuthed(true);
        } else {
          setAuthed(true);
        }
      } catch (e: any) {
        setError(e.message || "Не удалось войти");
        clearToken();
      } finally {
        setReady(true);
      }
    };
    run();
  }, []);

  if (!ready || (authed && me.isLoading)) {
    return <div className="app"><div className="display h1">Lumina</div><div className="skeleton" /></div>;
  }
  if (error && !me.data) {
    return (
      <div className="app empty">
        <h1 className="display">Lumina</h1>
        <p className="err">{error}</p>
        <button className="btn" onClick={() => location.reload()}><RefreshCw size={16} /> Повторить</button>
      </div>
    );
  }
  if (!me.data) return <div className="app"><div className="skeleton" /></div>;

  return (
    <Shell me={me.data}>
      <Routes>
        <Route path="/" element={<Home me={me.data} />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/product/:id" element={<ProductPage me={me.data} />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:id" element={<OrderPage />} />
        <Route path="/balance" element={<Balance me={me.data} />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/referrals" element={<Referrals />} />
        <Route path="/profile" element={<Profile me={me.data} />} />
        <Route path="/admin" element={isStaff(me.data.role) ? <AdminPage path="home" /> : <Navigate to="/" />} />
        <Route path="/admin/users" element={<AdminPage path="users" />} />
        <Route path="/admin/orders" element={<AdminPage path="orders" />} />
        <Route path="/admin/products" element={<AdminPage path="products" />} />
        <Route path="/admin/mirrors" element={<AdminPage path="mirrors" />} />
        <Route path="/admin/analytics" element={<AdminPage path="analytics" />} />
        <Route path="/admin/settings" element={<AdminPage path="settings" />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Shell>
  );
}
