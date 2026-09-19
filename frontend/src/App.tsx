import { useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import {
  Home as HomeIcon,
  Store,
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
  ArrowLeft,
} from "lucide-react";
import { api, ApiError, clearToken, setToken } from "./api/client";
import { formatRub, payStatusLabel, payStatusTone, statusLabel, statusTone } from "./lib/format";
import { bootTelegram, canPreviewDemo, haptic, isTelegramWebApp, prefersReducedMotion, sleep, waitForTelegram } from "./lib/telegram";
import { AssetPage, GalleryHome, GiftArt, RentListPage, RentNftPage } from "./Market";
import { TrustPayPage } from "./TrustPay";
import { AdminApp } from "./admin/Admin";
import { Preloader, TelegramGate } from "./Boot";
import { FilterBar } from "./Filters";
import { FulfillmentOverlay, type FulfillStage } from "./Fulfillment";
import { DigitalShop, DigitalProductPage, MyPurchases, PurchaseDetail } from "./Digital";
import { GiveawaysPage, GiveawayPage } from "./Giveaways";

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

type BootInfo = {
  app_name?: string;
  demo_login_enabled?: boolean;
  bot_username?: string | null;
  app_env?: string;
};

const isStaff = (role?: string) => ["MANAGER", "ADMIN", "SUPERADMIN", "MIRROR_OWNER"].includes(role || "");

function useMe(enabled: boolean) {
  return useQuery({
    queryKey: ["me"],
    enabled,
    queryFn: () => api<Me>("/me"),
  });
}

async function timed<T>(promise: Promise<T>, ms = 7000): Promise<T | null> {
  return Promise.race([
    promise,
    new Promise<null>((resolve) => setTimeout(() => resolve(null), ms)),
  ]);
}

async function prefetchShop(qc: QueryClient) {
  await Promise.allSettled([
    timed(qc.prefetchQuery({ queryKey: ["me"], queryFn: () => api<Me>("/me") })),
    timed(qc.prefetchQuery({
      queryKey: ["catalog", "", "all", "popular"],
      queryFn: () => api("/catalog?q=&category=all&sort=popular"),
    })),
    timed(qc.prefetchQuery({ queryKey: ["orders-home"], queryFn: () => api("/orders") })),
    timed(qc.prefetchQuery({ queryKey: ["rent-nft"], queryFn: () => api("/rent/nft/list") }), 5000),
    timed(qc.prefetchQuery({ queryKey: ["digital", "topup"], queryFn: () => api("/digital/catalog?group=topup") }), 4000),
    timed(qc.prefetchQuery({ queryKey: ["giveaways"], queryFn: () => api("/giveaways") }), 4000),
  ]);
}

function Shell({ me, children }: { me: Me; children: React.ReactNode }) {
  const loc = useLocation();
  const nav = [
    { to: "/", icon: HomeIcon, label: "Главная" },
    { to: "/catalog", icon: Store, label: "Каталог" },
    { to: "/giveaways", icon: Gift, label: "Розыгрыши" },
    { to: "/balance", icon: Wallet, label: "Баланс" },
    { to: "/profile", icon: UserRound, label: "Профиль" },
  ];
  const admin = loc.pathname.startsWith("/admin");
  const trust = loc.pathname.startsWith("/pay/");
  const asset = loc.pathname.startsWith("/asset/");
  const product = loc.pathname.startsWith("/product/");
  const detailNav = /^\/(digital|giveaways|purchases)\/[^/]+/.test(loc.pathname);
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
              ["/admin/digital", "Digital"],
              ["/admin/giveaways", "Розыгрыши"],
              ["/admin/promos", "Промокоды"],
              ["/admin/pricing", "Цены и акции"],
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
                ["/admin/promos", "Промо"],
                ["/admin/pricing", "Цены"],
                ["/admin/digital", "Коды"],
                ["/admin/giveaways", "Розыгрыши"],
                ["/admin/orders", "Заказы"],
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
      {!admin && !asset && !product && !detailNav && (
        <nav className="nav">
          {nav.map((n) => {
            const Icon = n.icon;
            const active = n.to === "/"
              ? loc.pathname === "/"
              : n.to === "/catalog"
                ? ["/catalog", "/digital", "/games", "/rent", "/nft", "/product"].some((p) => loc.pathname.startsWith(p))
                : loc.pathname.startsWith(n.to);
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
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  useEffect(() => { setCategory(initial); }, [initial]);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["catalog", q, category, sort, priceMin, priceMax],
    queryFn: () => {
      const p = new URLSearchParams({ q, category, sort });
      if (priceMin) p.set("price_min", priceMin);
      if (priceMax) p.set("price_max", priceMax);
      return api(`/catalog?${p}`);
    },
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Каталог</h1>
      <div className="row wrap">
        <Link to="/digital" className="btn ghost sm">Пополнения</Link>
        <Link to="/games" className="btn ghost sm">Игры</Link>
        <Link to="/giveaways" className="btn ghost sm">Розыгрыши</Link>
      </div>
      <FilterBar
        search={q}
        onSearch={setQ}
        categories={["all", "stars", "premium", "nft", "username", "number"].map((id) => ({ id, label: CAT_LABEL[id] }))}
        category={category}
        onCategory={setCategory}
        sorts={[
          { id: "popular", label: "Популярные" },
          { id: "new", label: "Новые" },
          { id: "price_asc", label: "Дешевле" },
          { id: "price_desc", label: "Дороже" },
        ]}
        sort={sort}
        onSort={setSort}
        priceMin={priceMin}
        priceMax={priceMax}
        onPriceMin={setPriceMin}
        onPriceMax={setPriceMax}
      />
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
            <div style={{ textAlign: "right" }}>
              {p.sale_percent && Number(p.sale_percent) > 0 ? <span className="badge ok">−{Number(p.sale_percent)}%</span> : null}
              {p.compare_at ? <div className="muted compare">{formatRub(p.compare_at)}</div> : null}
              <b className="num">{formatRub(p.preview_total)}</b>
            </div>
          </Link>
        );
      })}
      {!isLoading && !(data?.items || []).length && <div className="empty">Ничего не нашлось. Смягчите фильтры.</div>}
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
  const [promo, setPromo] = useState("");
  const [deal, setDeal] = useState<any>(null);
  const [ff, setFf] = useState<{ stage: FulfillStage; order?: any; error?: string } | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["product", id, qty],
    queryFn: () => api(`/products/${id}?quantity=${qty}`),
  });
  useEffect(() => {
    if (data?.kind === "premium") setQty(data.min_quantity);
  }, [data?.kind, data?.min_quantity]);
  useEffect(() => { setDeal(null); }, [qty, id]);
  const applyPromo = useMutation({
    mutationFn: () => api(`/promos/preview?code=${encodeURIComponent(promo)}&product_id=${id}&quantity=${qty}`),
    onSuccess: (d) => setDeal(d),
  });
  const buy = useMutation({
    mutationFn: () =>
      api("/orders", {
        method: "POST",
        body: JSON.stringify({
          product_id: Number(id),
          quantity: qty,
          recipient,
          idempotency_key: crypto.randomUUID(),
          promo_code: deal?.kind && deal.kind !== "balance" ? promo : undefined,
        }),
      }),
  });
  const runBuy = async () => {
    haptic("medium");
    setConfirm(false);
    setFf({ stage: "pay" });
    const quiet = prefersReducedMotion();
    const t0 = Date.now();
    try {
      const order = await buy.mutateAsync();
      const payWait = quiet ? 120 : Math.max(0, 900 - (Date.now() - t0));
      await sleep(payWait);
      setFf({ stage: "issue", order });
      await sleep(quiet ? 180 : 1600);
      haptic("success");
      setFf({ stage: "done", order });
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["orders-home"] });
    } catch (e: any) {
      haptic("error");
      setFf({ stage: "error", error: e.message || "Не удалось оплатить" });
    }
  };
  if (isLoading || !data) return <div className="skeleton tall" />;
  const presets = data.presets || [50, 100, 250, 500, 1000];
  const payable = deal?.kind && deal.kind !== "balance" && deal.new_total != null ? deal.new_total : data.total;
  const after = Number(me.balance) - Number(payable);
  const motif = data.kind === "premium" ? "diamond" : "star";
  const unitHint = data.kind === "stars" ? " / звезда" : data.kind === "premium" ? "" : " / мес.";
  return (
    <div className="grid product-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}>
        <ArrowLeft size={16} /> Назад
      </button>
      <div className="panel asset-hero">
        <GiftArt tone={data.kind === "premium" ? 42 : 210} motif={motif} emblem />
        <h1 className="h1 display">{data.name}</h1>
        <p className="muted lead">{data.description}</p>
        <div className="tiny">Текущая цена</div>
        {data.compare_at ? (
          <div className="h2 num">
            <span className="compare">{formatRub(Number(data.compare_at) / Math.max(1, data.quantity))}</span>{" "}
            {formatRub(data.unit_price)}{unitHint}
          </div>
        ) : (
          <div className="h2 num">{formatRub(data.unit_price)}{unitHint}</div>
        )}
        {data.sale_name ? <div className="badge ok">{data.sale_name} −{Number(data.sale_percent)}%</div> : null}
      </div>
      {data.kind === "stars" && (
        <>
          <div className="qty">
            <button type="button" onClick={() => setQty(Math.max(data.min_quantity, qty - data.step))}><Minus size={16} /></button>
            <b className="display num qty-val">{qty}</b>
            <button type="button" onClick={() => setQty(Math.min(data.max_quantity, qty + data.step))}><Plus size={16} /></button>
          </div>
          <div className="presets">
            {presets.map((p: number) => (
              <button key={p} className={qty === p ? "on" : ""} onClick={() => setQty(p)}>{p}</button>
            ))}
          </div>
        </>
      )}
      <input placeholder="Username получателя без @" value={recipient} onChange={(e) => setRecipient(e.target.value.replace("@", ""))} />
      <div className="promo-row">
        <input placeholder="Промокод" value={promo} onChange={(e) => { setPromo(e.target.value); setDeal(null); }} />
        <button className="btn ghost" type="button" disabled={!promo.trim() || applyPromo.isPending} onClick={() => applyPromo.mutate()}>
          Применить
        </button>
      </div>
      {applyPromo.error && <div className="err">{(applyPromo.error as ApiError).message}</div>}
      {deal?.kind === "balance" && <div className="muted">{deal.message}. Откройте Баланс, чтобы получить начисление.</div>}
      {deal?.kind && deal.kind !== "balance" && <div className="muted ok-line">{deal.message}</div>}
      <div className="panel pad">
        <div className="between"><span className="muted">Итог</span><b>{data.quantity} × {formatRub(data.unit_price)}</b></div>
        {data.compare_at && Number(data.compare_at) > Number(data.total) && (
          <div className="between"><span className="muted">Без акции</span><span className="compare">{formatRub(data.compare_at)}</span></div>
        )}
        {deal?.discount && Number(deal.discount) > 0 && (
          <div className="between"><span className="muted">Скидка</span><b>−{formatRub(deal.discount)}</b></div>
        )}
        <div className="between"><span className="muted">К оплате</span><b className="h2 num">{formatRub(payable)}</b></div>
        <div className="between"><span className="muted">Баланс</span><span className="num">{formatRub(me.balance)}</span></div>
      </div>
      {buy.error && !ff && <div className="err">{(buy.error as ApiError).message}</div>}
      <div className="asset-cta">
        <button className="btn block" onClick={() => { haptic("medium"); setConfirm(true); }}>Купить за {formatRub(payable)}</button>
      </div>
      {confirm && (
        <div className="sheet open" onClick={() => setConfirm(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2 display">Подтвердить заказ?</h2>
            <div>Товар: {data.name}</div>
            <div>Количество: {data.quantity}</div>
            <div>Цена: {formatRub(payable)}</div>
            <div>Баланс после: {formatRub(after)}</div>
            <div className="row">
              <button className="btn ghost block" onClick={() => setConfirm(false)}>Отмена</button>
              <button className="btn block" disabled={buy.isPending} onClick={runBuy}>Подтвердить</button>
            </div>
          </div>
        </div>
      )}
      {ff && (
        <FulfillmentOverlay
          stage={ff.stage}
          order={ff.order}
          productName={data.name}
          quantity={data.quantity}
          recipient={recipient}
          kind={data.kind}
          error={ff.error}
          onClose={() => setFf(null)}
        />
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
        {data.promo ? <div className="muted">Промокод {data.promo}{data.discount ? ` · скидка ${formatRub(data.discount)}` : ""}</div> : null}
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
  const qc = useQueryClient();
  const [amount, setAmount] = useState("500");
  const [code, setCode] = useState("");
  const { data } = useQuery({ queryKey: ["tx"], queryFn: () => api("/transactions") });
  const pays = useQuery({ queryKey: ["tp-list"], queryFn: () => api("/trust-pay/payments") });
  const create = useMutation({
    mutationFn: () => api("/trust-pay/payments", { method: "POST", body: JSON.stringify({ amount }) }),
    onSuccess: (p: any) => {
      haptic("medium");
      nav(`/pay/${p.public_id}`);
    },
  });
  const redeem = useMutation({
    mutationFn: () => api("/promos/redeem", { method: "POST", body: JSON.stringify({ code }) }),
    onSuccess: () => {
      haptic("success");
      setCode("");
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["tx"] });
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
        <div className="tiny">Промокод на баланс</div>
        <div className="promo-row">
          <input placeholder="Код" value={code} onChange={(e) => setCode(e.target.value)} />
          <button className="btn ghost" disabled={!code.trim() || redeem.isPending} onClick={() => redeem.mutate()}>Получить</button>
        </div>
        {redeem.error && <div className="err">{(redeem.error as ApiError).message}</div>}
        {redeem.data && <div className="muted">Начислено {formatRub(redeem.data.credited)}</div>}
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
            <b>{p.status === "paid" ? `+${formatRub(p.amount)}` : formatRub(p.amount)}</b>
            <div className="muted">Trust Pay · {p.public_id}</div>
            <div className="muted">Комиссия {formatRub(p.fee)} · перевод {formatRub(p.total)} · {p.created_at ? new Date(p.created_at).toLocaleString("ru") : ""}</div>
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
    ["/purchases", "Мои покупки", "Коды"],
    ["/giveaways", "Розыгрыши", "Призы"],
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
  const qc = useQueryClient();
  const [phase, setPhase] = useState<"boot" | "gate" | "app">("boot");
  const [bootLabel, setBootLabel] = useState("Подключаемся");
  const [bootInfo, setBootInfo] = useState<BootInfo | null>(null);
  const [authed, setAuthed] = useState(false);
  const [error, setError] = useState("");
  const me = useMe(authed);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      const started = Date.now();
      try {
        setBootLabel("Подключаемся");
        bootTelegram();
        const [info] = await Promise.all([
          api<BootInfo>("/public/boot").catch(() => ({ app_name: "Lumina", demo_login_enabled: false, bot_username: null })),
          waitForTelegram(650),
        ]);
        if (cancelled) return;
        setBootInfo(info);

        const onPay = window.location.pathname.startsWith("/pay/");
        const tg = bootTelegram();
        if (isTelegramWebApp() && tg?.initData) {
          setBootLabel("Проверяем вход");
          const data = await api("/auth/telegram", { method: "POST", body: JSON.stringify({ init_data: tg.initData }) });
          setToken(data.token);
          setAuthed(true);
          if (onPay) {
            if (!cancelled) setPhase("app");
            return;
          }
          setBootLabel("Загружаем витрину");
          await prefetchShop(qc);
          const wait = Math.max(0, 1100 - (Date.now() - started));
          if (wait) await sleep(wait);
          if (!cancelled) setPhase("app");
          return;
        }

        const leftover = Math.max(0, 1000 - (Date.now() - started));
        if (leftover) await sleep(leftover);
        if (!cancelled) {
          if (onPay) {
            setPhase("app");
            return;
          }
          clearToken();
          setPhase("gate");
        }
      } catch (e: any) {
        if (cancelled) return;
        if (window.location.pathname.startsWith("/pay/")) {
          setPhase("app");
          return;
        }
        setError(e.message || "Не удалось загрузить");
        setPhase("gate");
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [qc]);

  const enterDemo = async () => {
    setError("");
    setPhase("boot");
    setBootLabel("Загружаем витрину");
    try {
      const data = await api("/auth/demo", { method: "POST", body: JSON.stringify({ name: "Lumina" }) });
      setToken(data.token);
      setAuthed(true);
      await prefetchShop(qc);
      await sleep(prefersReducedMotion() ? 80 : 500);
      setPhase("app");
    } catch (e: any) {
      setError(e.message || "Не удалось войти");
      setPhase("gate");
    }
  };

  const onPay = typeof window !== "undefined" && window.location.pathname.startsWith("/pay/");

  if (onPay) {
    if (phase === "boot") return <Preloader label="Загружаем оплату" />;
    return (
      <Routes>
        <Route path="/pay/:id" element={<TrustPayPage />} />
      </Routes>
    );
  }

  if (phase === "boot" || (phase === "app" && authed && me.isLoading && !me.data)) {
    return <Preloader label={bootLabel} />;
  }
  if (phase === "gate" || (error && !me.data && phase !== "app")) {
    return (
      <TelegramGate
        info={bootInfo}
        allowDemo={canPreviewDemo(Boolean(bootInfo?.demo_login_enabled), bootInfo?.app_env)}
        error={error}
        onDemo={enterDemo}
      />
    );
  }
  if (!me.data) {
    return <Preloader label="Загружаем витрину" />;
  }
  if (me.isError) {
    return (
      <div className="boot-screen">
        <div className="boot-inner">
          <h1 className="display">Lumina</h1>
          <p className="err">Не удалось загрузить профиль</p>
          <button className="btn" onClick={() => location.reload()}><RefreshCw size={16} /> Повторить</button>
        </div>
      </div>
    );
  }

  return (
    <Shell me={me.data}>
      <Routes>
        <Route path="/" element={<Home me={me.data} />} />
        <Route path="/catalog" element={<Catalog />} />
        <Route path="/digital" element={<DigitalShop group="topup" />} />
        <Route path="/games" element={<DigitalShop group="games" />} />
        <Route path="/digital/:id" element={<DigitalProductPage me={me.data} />} />
        <Route path="/purchases" element={<MyPurchases />} />
        <Route path="/purchases/:id" element={<PurchaseDetail />} />
        <Route path="/giveaways" element={<GiveawaysPage />} />
        <Route path="/giveaways/:id" element={<GiveawayPage />} />
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
