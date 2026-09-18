import { useEffect, useState } from "react";
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
  Plus,
  Minus,
  Check,
  RefreshCw,
  Shield,
  Gift,
  Hash,
  AtSign,
} from "lucide-react";
import { api, ApiError, clearToken, getToken, setToken } from "./api/client";
import { formatRub, payStatusLabel, payStatusTone, statusLabel, statusTone } from "./lib/format";
import { bootTelegram, haptic } from "./lib/telegram";
import { AssetPage, GalleryHome, GiftArt, RentListPage, RentNftPage } from "./Market";
import { TrustPayPage } from "./TrustPay";

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
  const trust = loc.pathname.startsWith("/pay/");
  if (trust) {
    return <div className="trust-host">{children}</div>;
  }
  return (
    <div className={`app ${admin ? "admin" : ""}`}>
      {admin ? (
        <div className="admin-layout">
          <aside className="sidebar panel">
            <div className="row"><div className="logo-mark">L</div><b className="display">Lumina</b></div>
            {[
              ["/admin", "Дашборд"],
              ["/admin/users", "Пользователи"],
              ["/admin/orders", "Заказы"],
              ["/admin/products", "Товары"],
              ["/admin/mirrors", "Зеркала"],
              ["/admin/analytics", "Аналитика"],
              ["/admin/trust-pay", "Trust Pay"],
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
        <nav className="nav">
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
  return <GalleryHome me={me} />;
}

const CAT_LABEL: Record<string, string> = {
  all: "Все",
  stars: "Stars",
  premium: "Premium",
  nft: "NFT",
  username: "Username",
  number: "Номера",
};

function Catalog() {
  const loc = useLocation();
  const initial = new URLSearchParams(loc.search).get("category") || "all";
  const [q, setQ] = useState("");
  const [category, setCategory] = useState(initial);
  const [sort, setSort] = useState("popular");
  const [sheet, setSheet] = useState(false);
  useEffect(() => { setCategory(initial); }, [initial]);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["catalog", q, category, sort],
    queryFn: () => api(`/catalog?q=${encodeURIComponent(q)}&category=${category}&sort=${sort}`),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Каталог</h1>
      <input placeholder="Что вы ищете?" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="chips">
        {["all", "stars", "premium", "nft", "username", "number"].map((c) => (
          <button key={c} className={category === c ? "on" : ""} onClick={() => setCategory(c)}>
            {CAT_LABEL[c]}
          </button>
        ))}
        <button className="" onClick={() => setSheet(true)}>Фильтры</button>
      </div>
      {isLoading && <><div className="skeleton" /><div className="skeleton" /></>}
      {error && <div className="empty err">Не удалось загрузить данные<br /><button className="btn ghost" onClick={() => refetch()}>Повторить</button></div>}
      {(data?.items || []).map((p: any) => {
        const href = p.kind === "nft_rent" ? "/rent/nft" : p.kind === "nft_buy" ? "/nft" : p.kind === "username_rent" ? "/rent/username" : p.kind === "number_rent" ? "/rent/number" : `/product/${p.id}`;
        const icon = p.kind === "premium" ? <Crown size={20} /> : p.kind?.includes("nft") ? <Gift size={20} /> : p.kind?.includes("username") ? <AtSign size={20} /> : p.kind?.includes("number") ? <Hash size={20} /> : <Sparkles size={20} />;
        return (
          <Link key={p.id} to={href} className="panel product">
            <div className="icon-blob">{icon}</div>
            <div style={{ flex: 1 }}>
              <b>{p.name}</b>
              <div className="muted">{p.description}</div>
            </div>
            <b className="num">{formatRub(p.preview_total)}</b>
          </Link>
        );
      })}
      {sheet && (
        <div className="sheet open" onClick={() => setSheet(false)}>
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
  if (isLoading || !data) return <div className="skeleton tall" />;
  const presets = data.presets || [50, 100, 250, 500, 1000];
  const after = Number(me.balance) - Number(data.total);
  const motif = data.kind === "premium" ? "diamond" : "star";
  return (
    <div className="grid">
      <button className="btn ghost" onClick={() => nav(-1)}>Назад</button>
      <div className="panel asset-hero">
        <GiftArt tone={data.kind === "premium" ? 42 : 210} motif={motif} large />
        <h1 className="h1 display">{data.name}</h1>
        <p className="muted lead">{data.description}</p>
        <div className="tiny">Текущая цена</div>
        <div className="h2 num">{formatRub(data.unit_price)} {data.kind === "stars" ? " / звезда" : " / мес."}</div>
      </div>
      {data.kind === "stars" && (
        <>
          <div className="qty">
            <button onClick={() => setQty(Math.max(data.min_quantity, qty - data.step))}><Minus size={16} /></button>
            <b className="display num qty-val">{qty}</b>
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
      <div className="panel pad">
        <div className="between"><span className="muted">Итог</span><b>{data.quantity} × {formatRub(data.unit_price)}</b></div>
        <div className="between"><span className="muted">К оплате</span><b className="h2 num">{formatRub(data.total)}</b></div>
        <div className="between"><span className="muted">Баланс</span><span className="num">{formatRub(me.balance)}</span></div>
      </div>
      {buy.error && <div className="err">{(buy.error as ApiError).message}</div>}
      <button className="btn block" onClick={() => { haptic("medium"); setConfirm(true); }}>Купить за {formatRub(data.total)}</button>
      {confirm && (
        <div className="sheet open" onClick={() => setConfirm(false)}>
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
        <div className="sheet open">
          <div className="panel grid success-sheet">
            <div className="success-mark"><Check size={40} /></div>
            <h2 className="h2 display">Заказ одобрен</h2>
            <div className="muted">Заказ передан</div>
            <div className="ticket-line">#{done.public_id}</div>
            <div>Товар: {data.name}</div>
            <div>Количество: {done.quantity}</div>
            <div className="h2">{formatRub(done.total_price)}</div>
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
        <Link key={o.id} to={`/orders/${o.public_id}`} className="panel product">
          <div>
            <b>#{o.public_id}</b>
            <div className="muted">{o.product?.name} · {o.quantity}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="num">{formatRub(o.total_price)}</div>
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
      <div className="panel pad">
        <div>{data.product?.name}</div>
        <div className="muted">Количество: {data.quantity}</div>
        <div className="h2 num">Итог: {formatRub(data.total_price)}</div>
        <span className={`badge ${statusTone(data.status)}`}>{statusLabel(data.status)}</span>
      </div>
      <div className="panel pad">
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
  const nav = useNavigate();
  const [amount, setAmount] = useState("500");
  const { data } = useQuery({ queryKey: ["tx"], queryFn: () => api("/transactions") });
  const pays = useQuery({ queryKey: ["tp-list"], queryFn: () => api("/trust-pay/payments") });
  const create = useMutation({
    mutationFn: () => api("/trust-pay/payments", { method: "POST", body: JSON.stringify({ amount }) }),
    onSuccess: (p: any) => {
      haptic("medium");
      nav(`/pay/${p.public_id}`);
    },
  });
  return (
    <div className="grid">
      <div className="panel ledger" style={{ textAlign: "center" }}>
        <div className="tiny">Баланс</div>
        <div className="h1 display num" style={{ fontSize: 40 }}>{formatRub(me.balance)}</div>
      </div>
      <div className="panel pad grid">
        <div className="tiny">Trust Pay</div>
        <h2 className="h2">Пополнить баланс</h2>
        <p className="muted">Минимум 30 ₽. Комиссия 3% сверху. Перевод по номеру карты — сумма вводится здесь или в боте, на странице оплаты её изменить нельзя.</p>
        <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(",", "."))} placeholder="Сумма пополнения" />
        <div className="presets">
          {["100", "300", "500", "1000", "2000"].map((n) => (
            <button key={n} className={amount === n ? "on" : ""} onClick={() => setAmount(n)}>{n} ₽</button>
          ))}
        </div>
        {create.error && <div className="err">{(create.error as ApiError).message}</div>}
        <button className="btn block" disabled={create.isPending} onClick={() => create.mutate()}>Перейти к оплате</button>
      </div>
      <h2 className="h2">История операций</h2>
      {(pays.data?.items || []).map((p: any) => (
        <Link key={p.public_id} to={`/pay/${p.public_id}`} className="between panel pad">
          <div>
            <b>Trust Pay · {p.public_id}</b>
            <div className="muted">{formatRub(p.amount)} + комиссия {formatRub(p.fee)} · перевод {formatRub(p.total)}</div>
            <div className="muted">{p.created_at ? new Date(p.created_at).toLocaleString("ru") : ""}</div>
          </div>
          <span className={`badge ${payStatusTone(p.status)}`}>{payStatusLabel(p.status)}</span>
        </Link>
      ))}
      {(data?.items || []).length === 0 && !(pays.data?.items || []).length && <div className="empty">История операций пуста</div>}
      {(data?.items || []).map((t: any) => (
        <div key={t.id} className="between panel pad">
          <div>
            <b>{t.description}</b>
            <div className="muted">{new Date(t.created_at).toLocaleString("ru")}</div>
          </div>
          <b className="num" style={{ color: Number(t.amount) < 0 ? "var(--rose)" : "var(--mint)" }}>
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
      <div className="panel pad">
        <div className="tiny">Ваш код</div>
        <h2 className="h2">{data.code}</h2>
        <div className="muted">Награда {data.percent}% с покупок друзей</div>
        <p style={{ wordBreak: "break-all" }}>{data.link}</p>
        <button className="btn block" onClick={() => navigator.clipboard.writeText(data.link)}>Скопировать ссылку</button>
      </div>
      <div className="row">
        <div className="panel pad" style={{ flex: 1 }}><div className="tiny">Приглашено</div><b>{data.invited}</b></div>
        <div className="panel pad" style={{ flex: 1 }}><div className="tiny">Заработано</div><b>{formatRub(data.earned)}</b></div>
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
      <div className="panel product">
        <div className="logo-mark">{(me.first_name || "L")[0]}</div>
        <div>
          <h2 className="h2">{me.first_name}</h2>
          <div className="muted">@{me.username || "user"} · {me.role}</div>
        </div>
      </div>
      {cards.map(([to, t, s]) => (
        <Link key={to} to={to} className="panel between pad">
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
        <div key={t.id} className="panel between pad">
          <div><b>{t.description}</b><div className="muted">{t.type}</div></div>
          <b className="num">{formatRub(t.amount)}</b>
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
  const trustPays = useQuery({ queryKey: ["adm-tp"], queryFn: () => api("/admin/trust-pay"), enabled: path === "trust-pay" });
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
  const confirmPay = useMutation({
    mutationFn: (id: number | string) => api(`/admin/trust-pay/${id}/confirm`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-tp"] }),
  });
  const failPay = useMutation({
    mutationFn: (id: number | string) => api(`/admin/trust-pay/${id}/fail`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-tp"] }),
  });

  if (path === "users") {
    return (
      <div className="grid">
        <h1 className="h1 display">Пользователи</h1>
        {(users.data?.items || []).map((u: any) => (
          <div key={u.id} className="panel between pad">
            <div><b>{u.first_name} @{u.username}</b><div className="muted">{u.role}</div></div>
            <div className="num">{formatRub(u.balance)}</div>
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
          <div key={o.id} className="panel between pad">
            <div><b>#{o.public_id}</b><div className="muted">{o.product?.name} · {o.recipient}</div></div>
            <div>
              <div className="num">{formatRub(o.total_price)}</div>
              <button className="btn ghost sm" onClick={() => refund.mutate(o.id)}>Возврат</button>
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
          <div key={p.id} className="panel between pad">
            <div><b>{p.name}</b><div className="muted">{p.category}</div></div>
            <button className="btn ghost sm" onClick={() => patchProduct.mutate({ id: p.id, enabled: !p.enabled })}>{p.enabled ? "Выкл" : "Вкл"}</button>
          </div>
        ))}
      </div>
    );
  }
  if (path === "mirrors") {
    return (
      <div className="grid">
        <h1 className="h1 display">Зеркала</h1>
        <div className="panel grid pad">
          <b>Создать зеркало</b>
          <input value={mirror.name} onChange={(e) => setMirror({ ...mirror, name: e.target.value })} placeholder="Название" />
          <input value={mirror.slug} onChange={(e) => setMirror({ ...mirror, slug: e.target.value })} placeholder="slug" />
          <input value={mirror.markup_percent} onChange={(e) => setMirror({ ...mirror, markup_percent: e.target.value })} placeholder="Наценка %" />
          <div className="panel pad">
            <div className="tiny">Preview</div>
            <b>{mirror.name}</b>
            <div className="muted">{mirror.description} · +{mirror.markup_percent}%</div>
          </div>
          <button className="btn" onClick={() => createMirror.mutate()}>Создать</button>
        </div>
        {(mirrors.data?.items || []).map((m: any) => (
          <div key={m.id} className="panel between pad">
            <div><b>{m.name}</b><div className="muted">/{m.slug} · {m.orders} заказов</div></div>
            <div className="num">{formatRub(m.revenue)}</div>
          </div>
        ))}
      </div>
    );
  }
  if (path === "trust-pay") {
    return (
      <div className="grid">
        <h1 className="h1 display">Trust Pay</h1>
        {(trustPays.data?.items || []).map((p: any) => (
          <div key={p.id} className="panel pad grid">
            <div className="between">
              <b>{p.public_id}</b>
              <span className={`badge ${payStatusTone(p.status)}`}>{payStatusLabel(p.status)}</span>
            </div>
            <div className="muted">user {p.user_id} · tg {p.telegram_id} · @{p.username || "—"}</div>
            <div className="num">{formatRub(p.amount)} + {formatRub(p.fee)} = {formatRub(p.total)}</div>
            <div className="muted">{p.created_at ? new Date(p.created_at).toLocaleString("ru") : ""}{p.paid_at ? ` · paid ${new Date(p.paid_at).toLocaleString("ru")}` : ""}</div>
            {(p.status === "pending" || p.status === "processing") && (
              <div className="row">
                <button className="btn" onClick={() => confirmPay.mutate(p.id)}>Подтвердить</button>
                <button className="btn ghost" onClick={() => failPay.mutate(p.id)}>Отклонить</button>
              </div>
            )}
          </div>
        ))}
        {!(trustPays.data?.items || []).length && <div className="empty">Платежей пока нет</div>}
      </div>
    );
  }
  if (path === "analytics") {
    const series = analytics.data?.series || [];
    const max = Math.max(1, ...series.map((s: any) => Number(s.revenue)));
    return (
      <div className="grid">
        <h1 className="h1 display">Аналитика</h1>
        <div className="panel pad">
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
        <div className="panel pad">
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
          <div key={String(t)} className="panel pad">
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
        <Route path="/rent/nft" element={<RentNftPage mode="rent" />} />
        <Route path="/nft" element={<RentNftPage mode="buy" />} />
        <Route path="/rent/username" element={<RentListPage kind="username_rent" />} />
        <Route path="/rent/number" element={<RentListPage kind="number_rent" />} />
        <Route path="/asset/:kind/:address" element={<AssetPage me={me.data} />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:id" element={<OrderPage />} />
        <Route path="/balance" element={<Balance me={me.data} />} />
        <Route path="/pay/:id" element={<TrustPayPage />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/referrals" element={<Referrals />} />
        <Route path="/profile" element={<Profile me={me.data} />} />
        <Route path="/admin" element={isStaff(me.data.role) ? <AdminPage path="home" /> : <Navigate to="/" />} />
        <Route path="/admin/users" element={<AdminPage path="users" />} />
        <Route path="/admin/orders" element={<AdminPage path="orders" />} />
        <Route path="/admin/products" element={<AdminPage path="products" />} />
        <Route path="/admin/mirrors" element={<AdminPage path="mirrors" />} />
        <Route path="/admin/analytics" element={<AdminPage path="analytics" />} />
        <Route path="/admin/trust-pay" element={<AdminPage path="trust-pay" />} />
        <Route path="/admin/settings" element={<AdminPage path="settings" />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Shell>
  );
}
