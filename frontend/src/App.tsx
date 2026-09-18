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
import { AdminApp } from "./admin/Admin";

type Me = {
  id: number;
  telegram_id?: number;
  first_name?: string;
  username?: string;
  role: string;
  balance: string;
  orders_count: number;
  spent: string;
  referral_code: string;
  photo_url?: string;
  is_owner?: boolean;
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
  const asset = loc.pathname.startsWith("/asset/");
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
              ["/admin/trust-pay", "Trust Pay"],
              ["/admin/users", "Пользователи"],
              ["/admin/staff", "Команда"],
              ["/admin/orders", "Заказы"],
              ["/admin/transactions", "Транзакции"],
              ["/admin/products", "Товары"],
              ["/admin/mirrors", "Зеркала"],
              ["/admin/analytics", "Аналитика"],
              ...(me.role === "ADMIN" || me.role === "SUPERADMIN" ? [["/admin/audit", "Журнал"]] : []),
              ...(me.role === "SUPERADMIN" ? [["/admin/settings", "Настройки"]] : []),
            ].map(([to, label]) => {
              const active = to === "/admin" ? loc.pathname === "/admin" : loc.pathname.startsWith(to);
              return (
                <Link key={to} to={to} className={active ? "btn block" : "btn ghost block"}>{label}</Link>
              );
            })}
            <Link to="/" className="btn ghost block">В магазин</Link>
          </aside>
          <div>
            <nav className="admin-tabs">
              {[
                ["/admin", "Дашборд"],
                ["/admin/trust-pay", "Платежи"],
                ["/admin/users", "Люди"],
                ["/admin/orders", "Заказы"],
                ["/admin/transactions", "Движения"],
              ].map(([to, label]) => {
                const active = to === "/admin" ? loc.pathname === "/admin" : loc.pathname.startsWith(to);
                return (
                  <Link key={to} to={to} className={active ? "on" : ""}>{label}</Link>
                );
              })}
            </nav>
            {children}
          </div>
        </div>
      ) : (
        children
      )}
      {!admin && !asset && (
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
  const parsed = Number(amount);
  const canPay = Number.isFinite(parsed) && parsed >= 30;
  return (
    <div className="grid">
      <div className="panel ledger" style={{ textAlign: "center" }}>
        <div className="tiny">Баланс</div>
        <div className="h1 display num" style={{ fontSize: 40 }}>{formatRub(me.balance)}</div>
      </div>
      <div className="panel pad grid">
        <div className="tiny">Пополнение</div>
        <h2 className="h2">Сначала укажите сумму</h2>
        <p className="muted">Минимум 30 ₽, комиссия 3% сверху. Без суммы ссылка на карту и ЮMoney не выдаётся. Перевод — на 5599 0021 4495 5509 или через ЮMoney.</p>
        <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(",", "."))} placeholder="Сумма пополнения" />
        <div className="presets">
          {["100", "300", "500", "1000", "2000"].map((n) => (
            <button key={n} className={amount === n ? "on" : ""} onClick={() => setAmount(n)}>{n} ₽</button>
          ))}
        </div>
        {create.error && <div className="err">{(create.error as ApiError).message}</div>}
        <button className="btn block" disabled={create.isPending || !canPay} onClick={() => create.mutate()}>
          {canPay ? "Открыть оплату" : "Укажите сумму от 30 ₽"}
        </button>
      </div>
      <h2 className="h2">История операций</h2>
      {(pays.data?.items || []).map((p: any) => (
        <Link key={p.public_id} to={`/pay/${p.public_id}`} className="between panel pad">
          <div>
            <b>Пополнение · {p.public_id}</b>
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
        <Route path="/admin/*" element={isStaff(me.data.role) ? <AdminApp me={me.data} /> : <Navigate to="/" />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Shell>
  );
}
