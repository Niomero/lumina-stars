import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Minus, Plus } from "lucide-react";
import { api, ApiError } from "./api/client";
import { formatRub, statusLabel, statusTone } from "./lib/format";
import { haptic } from "./lib/telegram";
import { FilterBar } from "./Filters";

type Asset = {
  address: string;
  name: string;
  price_per_day: string;
  buy_price?: string;
  min_days: number;
  max_days: number;
  collection?: string;
  collection_name?: string;
  tone?: number;
  motif?: string;
  length?: number;
  digits?: string;
  kind: string;
  product_id?: number;
  image?: string | null;
  compare_at?: string | null;
  compare_at_buy?: string | null;
  sale_percent?: string;
  sale_name?: string | null;
};

const GLYPHS: Record<string, ReactNode> = {
  pepe: (
    <svg viewBox="0 0 64 64" fill="none">
      <ellipse cx="32" cy="36" rx="20" ry="16" fill="currentColor" opacity=".9" />
      <circle cx="22" cy="28" r="8" fill="currentColor" />
      <circle cx="42" cy="28" r="8" fill="currentColor" />
      <circle cx="22" cy="28" r="3.2" fill="#141210" />
      <circle cx="42" cy="28" r="3.2" fill="#141210" />
      <path d="M24 42c5 4 11 4 16 0" stroke="#141210" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  rose: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M32 14c8 4 12 12 8 18-4 6-12 6-16 1" stroke="currentColor" strokeWidth="2.4" />
      <circle cx="32" cy="28" r="7" fill="currentColor" />
      <path d="M32 36v16M26 46c4-4 8-4 12 0" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  ring: (
    <svg viewBox="0 0 64 64" fill="none">
      <ellipse cx="32" cy="38" rx="16" ry="10" stroke="currentColor" strokeWidth="3" />
      <path d="M24 30l8-12 8 12" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
      <path d="M28 30h8" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  diamond: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M16 26h32L32 52 16 26Z" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
      <path d="M16 26l8-10h16l8 10M24 16l8 10 8-10M32 26v26" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  peach: (
    <svg viewBox="0 0 64 64" fill="none">
      <circle cx="30" cy="36" r="16" fill="currentColor" />
      <path d="M32 20c6-8 16-6 16 2" stroke="currentColor" strokeWidth="2.2" />
      <ellipse cx="40" cy="22" rx="7" ry="4" fill="currentColor" opacity=".7" />
    </svg>
  ),
  bag: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M20 26h24l2 24H18l2-24Z" stroke="currentColor" strokeWidth="2.2" />
      <path d="M24 26c0-8 16-8 16 0" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="32" cy="38" r="3" fill="currentColor" />
    </svg>
  ),
  wine: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M26 12h12v10c8 6 8 16 0 22H26c-8-6-8-16 0-22V12Z" stroke="currentColor" strokeWidth="2.2" />
      <path d="M32 44v10M24 54h16" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  cigar: (
    <svg viewBox="0 0 64 64" fill="none">
      <rect x="10" y="28" width="38" height="10" rx="5" stroke="currentColor" strokeWidth="2.2" />
      <path d="M20 28v10M48 30c6 2 8 6 6 10" stroke="currentColor" strokeWidth="2" />
    </svg>
  ),
  cake: (
    <svg viewBox="0 0 64 64" fill="none">
      <rect x="14" y="30" width="36" height="18" rx="3" stroke="currentColor" strokeWidth="2.2" />
      <path d="M14 38h36M24 22v8M32 18v12M40 22v8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="24" cy="20" r="2" fill="currentColor" />
      <circle cx="32" cy="16" r="2" fill="currentColor" />
      <circle cx="40" cy="20" r="2" fill="currentColor" />
    </svg>
  ),
  star: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M32 10l5 16h16l-13 10 5 16-13-10-13 10 5-16-13-10h16z" fill="currentColor" />
    </svg>
  ),
  teddy: (
    <svg viewBox="0 0 64 64" fill="none">
      <circle cx="20" cy="22" r="8" fill="currentColor" />
      <circle cx="44" cy="22" r="8" fill="currentColor" />
      <circle cx="32" cy="36" r="16" fill="currentColor" />
      <circle cx="26" cy="34" r="2.4" fill="#141210" />
      <circle cx="38" cy="34" r="2.4" fill="#141210" />
      <ellipse cx="32" cy="42" rx="4" ry="3" fill="#141210" />
    </svg>
  ),
  heart: (
    <svg viewBox="0 0 64 64" fill="none">
      <path d="M32 50S12 36 12 24c0-7 6-12 12-12 5 0 8 3 8 6 0-3 3-6 8-6 6 0 12 5 12 12 0 12-20 26-20 26Z" fill="currentColor" />
    </svg>
  ),
  ice: (
    <svg viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="24" r="12" fill="currentColor" />
      <path d="M22 30l10 24 10-24" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
    </svg>
  ),
  bento: (
    <svg viewBox="0 0 64 64" fill="none">
      <rect x="12" y="18" width="40" height="30" rx="6" stroke="currentColor" strokeWidth="2.2" />
      <path d="M12 28h40M32 28v20" stroke="currentColor" strokeWidth="2" />
      <circle cx="22" cy="38" r="4" fill="currentColor" />
      <rect x="38" y="34" width="8" height="10" rx="2" fill="currentColor" />
    </svg>
  ),
  crystal: (
    <svg viewBox="0 0 64 64" fill="none">
      <circle cx="32" cy="32" r="16" stroke="currentColor" strokeWidth="2.2" />
      <path d="M32 16v32M16 32h32M22 22l20 20M42 22 22 42" stroke="currentColor" strokeWidth="1.6" opacity=".7" />
    </svg>
  ),
  gift: (
    <svg viewBox="0 0 64 64" fill="none">
      <rect x="14" y="26" width="36" height="24" rx="4" stroke="currentColor" strokeWidth="2.2" />
      <path d="M32 26v24M14 34h36M24 26c4-8 8-8 8 0 0-8 4-8 8 0" stroke="currentColor" strokeWidth="2.2" />
    </svg>
  ),
};

function prettyName(kind: string, name?: string, address?: string) {
  const raw = (name || "").trim();
  if (kind === "username_rent") {
    const handle = raw.replace(/^@/, "") || (address || "").replace(/^@/, "");
    if (handle.startsWith("EQ")) return "Username";
    return `@${handle}`;
  }
  if (kind === "number_rent") {
    if (!raw || raw.startsWith("EQ")) return "Номер";
    return raw.startsWith("+") ? raw : `+${raw}`;
  }
  if (!raw || raw.startsWith("EQ")) return "Подарок";
  return raw;
}

export function GiftArt({
  tone,
  motif,
  name,
  large,
  emblem,
  image,
}: {
  tone?: number;
  motif?: string;
  name?: string;
  large?: boolean;
  emblem?: boolean;
  image?: string | null;
}) {
  const [broken, setBroken] = useState(false);
  const key = motif || "gift";
  const size = emblem ? "emblem" : large ? "lg" : "";
  if (image && !broken) {
    return (
      <div className={`gift-art photo ${size}`} aria-hidden>
        <img src={image} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} />
        {name ? <span className="sr-only">{name}</span> : null}
      </div>
    );
  }
  return (
    <div className={`gift-art ${size}`} style={{ ["--tone" as string]: String(tone ?? 210) }} aria-hidden>
      <div className="gift-plate">{GLYPHS[key] || GLYPHS.gift}</div>
      {name ? <span className="sr-only">{name}</span> : null}
    </div>
  );
}

function Success({
  order,
  title,
  extra,
}: {
  order: any;
  title: string;
  extra?: React.ReactNode;
}) {
  return (
    <div className="sheet open">
      <div className="panel grid success-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="success-mark"><Check size={32} /></div>
        <h2 className="h2 display">Заказ одобрен</h2>
        <p className="muted">Заказ передан</p>
        <div className="ticket-line">#{order.public_id}</div>
        <div>{title}</div>
        <div className="h2">{formatRub(order.total_price)}</div>
        {extra}
        <Link className="btn block" to={`/orders/${order.public_id}`}>Посмотреть заказ</Link>
      </div>
    </div>
  );
}

function productByKind(items: any[] | undefined, kind: string) {
  return (items || []).find((p: any) => p.kind === kind);
}

export function GalleryHome({ me }: { me: { first_name?: string; balance: string } }) {
  const nfts = useQuery({ queryKey: ["rent-nft"], queryFn: () => api("/rent/nft/list") });
  const orders = useQuery({ queryKey: ["orders-home"], queryFn: () => api("/orders") });
  const featured = (nfts.data?.items || []).slice(0, 6);
  const recent = (orders.data?.items || []).slice(0, 2);
  return (
    <div className="grid gallery">
      <header className="hero-row">
        <div>
          <div className="tiny">Lumina</div>
          <h1 className="h1 display">Привет, {me.first_name || "гость"}</h1>
        </div>
        <Link to="/profile" className="logo-mark" aria-label="Профиль">L</Link>
      </header>

      <div className="panel ledger">
        <div className="tiny">Баланс</div>
        <div className="between">
          <div className="h1 display num">{formatRub(me.balance)}</div>
          <Link to="/balance" className="btn ghost sm">Пополнить</Link>
        </div>
      </div>

      <div className="section-label">Отделения</div>
      <div className="doors">
        <Link to="/catalog?category=stars" className="panel door">
          <span className="idx">01</span>
          <span className="tiny">Digital</span>
          <span className="h2 display">Stars</span>
        </Link>
        <Link to="/catalog?category=premium" className="panel door">
          <span className="idx">02</span>
          <span className="tiny">Подписка</span>
          <span className="h2 display">Premium</span>
        </Link>
        <Link to="/rent/nft" className="panel door">
          <span className="idx">03</span>
          <span className="tiny">Подарки</span>
          <span className="h2 display">NFT аренда</span>
        </Link>
        <Link to="/rent/username" className="panel door">
          <span className="idx">04</span>
          <span className="tiny">Имена</span>
          <span className="h2 display">Username</span>
        </Link>
        <Link to="/rent/number" className="panel door">
          <span className="idx">05</span>
          <span className="tiny">Связь</span>
          <span className="h2 display">Номера</span>
        </Link>
        <Link to="/nft" className="panel door">
          <span className="idx">06</span>
          <span className="tiny">Коллекция</span>
          <span className="h2 display">Купить NFT</span>
        </Link>
      </div>

      <div className="between">
        <h2 className="h2 display">Витрина подарков</h2>
        <Link to="/rent/nft" className="subtle">Смотреть</Link>
      </div>
      {nfts.isLoading && <div className="gift-grid">{[1, 2, 3, 4].map((i) => <div key={i} className="skeleton tall" />)}</div>}
      {!nfts.isLoading && featured.length === 0 && <div className="empty">Подарки загружаются с витрины</div>}
      <div className="gift-grid">
        {featured.map((g: Asset) => (
          <Link key={g.address} to={`/asset/nft_rent/${g.address}`} className="panel gift">
            <GiftArt tone={g.tone} motif={g.motif} name={g.name} image={g.image} />
            <b>{prettyName("nft_rent", g.name, g.address)}</b>
            <div className="muted">{formatRub(g.price_per_day)} / день</div>
          </Link>
        ))}
      </div>

      {recent.length > 0 && (
        <>
          <div className="between">
            <h2 className="h2 display">Последние заказы</h2>
            <Link to="/orders" className="subtle">Все</Link>
          </div>
          {recent.map((o: any) => (
            <Link key={o.id} to={`/orders/${o.public_id}`} className="panel product">
              <div>
                <b>#{o.public_id}</b>
                <div className="muted">{o.product?.name}</div>
              </div>
              <span className={`badge ${statusTone(o.status)}`}>{statusLabel(o.status)}</span>
            </Link>
          ))}
        </>
      )}
    </div>
  );
}

export function RentNftPage({ mode }: { mode: "rent" | "buy" }) {
  const kind = mode === "buy" ? "nft_buy" : "nft_rent";
  const path = mode === "buy" ? "/nft/buy/list" : "/rent/nft/list";
  const colsPath = mode === "buy" ? "/nft/buy/collections" : "/rent/nft/collections";
  const [col, setCol] = useState<string>("");
  const [sort, setSort] = useState("");
  const [q, setQ] = useState("");
  const cols = useQuery({ queryKey: [colsPath], queryFn: () => api(colsPath) });
  const collections = cols.data?.items || [];
  useEffect(() => {
    if (!col && collections[0]?.address) setCol(collections[0].address);
  }, [collections, col]);
  const list = useQuery({
    queryKey: [path, col, sort],
    enabled: mode === "buy" ? true : Boolean(col) || collections.length === 0,
    queryFn: () => {
      const q = new URLSearchParams();
      if (col) q.set("collection_address", col);
      if (mode === "buy" && sort) q.set("sort_order", sort);
      if (mode === "rent" && sort) q.set("sort_by", sort === "asc" ? "price_per_day" : sort);
      const s = q.toString();
      return api(`${path}${s ? `?${s}` : ""}`);
    },
  });
  return (
    <div className="grid">
      <h1 className="h1 display">{mode === "buy" ? "Купить NFT" : "Аренда NFT"}</h1>
      <p className="muted lead">
        {mode === "buy" ? "Gift NFT с живой витрины Fragment." : "Аренда Gift NFT. Каталог с tgstars.tg."}
      </p>
      <FilterBar
        search={q}
        onSearch={setQ}
        searchPlaceholder={mode === "buy" ? "Найти подарок" : "Найти NFT"}
        categories={[{ id: "", label: "Все коллекции" }, ...collections.map((c: any) => ({ id: c.address, label: c.name }))]}
        category={col}
        onCategory={setCol}
        sorts={[
          { id: "", label: "Новые" },
          { id: "asc", label: "Дешевле" },
          { id: "desc", label: "Дороже" },
        ]}
        sort={sort}
        onSort={setSort}
      />
      {list.isLoading && <div className="gift-grid">{[1, 2, 3, 4].map((i) => <div key={i} className="skeleton tall" />)}</div>}
      <div className="gift-grid">
        {(list.data?.items || []).filter((g: Asset) => !q || (g.name || "").toLowerCase().includes(q.toLowerCase())).map((g: Asset) => (
          <Link key={g.address} to={`/asset/${kind}/${g.address}`} className="panel gift">
            <GiftArt tone={g.tone} motif={g.motif} name={g.name} image={g.image} />
            <b>{prettyName(kind, g.name, g.address)}</b>
            <div className="muted">
              {g.sale_percent && Number(g.sale_percent) > 0 ? <span className="badge ok">−{Number(g.sale_percent)}%</span> : null}{" "}
              {mode === "buy" ? (
                <>
                  {g.compare_at_buy ? <span className="compare">{formatRub(g.compare_at_buy)} </span> : null}
                  {formatRub(g.buy_price || g.price_per_day)}
                </>
              ) : (
                <>
                  {g.compare_at ? <span className="compare">{formatRub(g.compare_at)} </span> : null}
                  {formatRub(g.price_per_day)} / день
                </>
              )}
            </div>
          </Link>
        ))}
      </div>
      {!list.isLoading && !(list.data?.items || []).length && (
        <div className="empty">{list.data?.error || "В этой коллекции пока пусто"}</div>
      )}
    </div>
  );
}

export function RentListPage({ kind }: { kind: "username_rent" | "number_rent" }) {
  const [q, setQ] = useState("");
  const [len, setLen] = useState<string>("");
  const [numbers, setNumbers] = useState("");
  const [underscore, setUnderscore] = useState("");
  const path = kind === "username_rent" ? "/rent/username/list" : "/rent/number/list";
  const list = useQuery({
    queryKey: [path, q, len, numbers, underscore],
    queryFn: () => {
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      if (kind === "username_rent" && len) p.append("length_filter", len);
      if (kind === "username_rent" && numbers) p.set("numbers_filter", numbers);
      if (kind === "username_rent" && underscore) p.set("underscore_filter", underscore);
      const s = p.toString();
      return api(`${path}${s ? `?${s}` : ""}`);
    },
  });
  const items = (list.data?.items || []).filter((g: Asset) => {
    if (kind !== "number_rent" || !q) return true;
    return `${g.name || ""} ${g.digits || ""}`.toLowerCase().includes(q.toLowerCase());
  });
  return (
    <div className="grid">
      <h1 className="h1 display">{kind === "username_rent" ? "Username" : "Номера"}</h1>
      <p className="muted lead">
        {kind === "username_rent" ? "Коллекционные Telegram-имена с витрины tgstars.tg." : "Анонимные Telegram-номера +888 с витрины tgstars.tg."}
      </p>
      <FilterBar
        search={q}
        onSearch={setQ}
        searchPlaceholder={kind === "username_rent" ? "Поиск имени" : "Поиск номера"}
        categories={kind === "username_rent" ? [
          { id: "", label: "Любая длина" },
          { id: "4", label: "4" },
          { id: "5", label: "5" },
          { id: "6", label: "6" },
          { id: "7", label: "7+" },
        ] : undefined}
        category={kind === "username_rent" ? len : undefined}
        onCategory={kind === "username_rent" ? setLen : undefined}
        extras={kind === "username_rent" ? (
          <>
            <div className="filter-row quiet">
              {[
                ["", "Цифры: все"],
                ["with", "С цифрами"],
                ["without", "Без цифр"],
              ].map(([id, label]) => (
                <button key={id || "n-all"} type="button" className={numbers === id ? "on" : ""} onClick={() => setNumbers(id)}>{label}</button>
              ))}
            </div>
            <div className="filter-row quiet">
              {[
                ["", "Подчёркивание: все"],
                ["with", "С _"],
                ["without", "Без _"],
              ].map(([id, label]) => (
                <button key={id || "u-all"} type="button" className={underscore === id ? "on" : ""} onClick={() => setUnderscore(id)}>{label}</button>
              ))}
            </div>
          </>
        ) : undefined}
      />
      {list.isLoading && <div className="skeleton" />}
      {items.map((g: Asset) => (
        <Link key={g.address} to={`/asset/${kind}/${g.address}`} className="panel handle-row between">
          <div>
            <b className="display handle">{prettyName(kind, g.name, g.address)}</b>
            <div className="muted">
              {g.compare_at ? <span className="compare">{formatRub(g.compare_at)} </span> : null}
              {formatRub(g.price_per_day)} / день
              {g.sale_percent && Number(g.sale_percent) > 0 ? <span className="badge ok"> −{Number(g.sale_percent)}%</span> : null}
            </div>
          </div>
          <span className="badge">Аренда</span>
        </Link>
      ))}
      {!list.isLoading && !items.length && (
        <div className="empty">{list.data?.error || "Ничего не нашлось"}</div>
      )}
    </div>
  );
}

function Aftercare({ order, kind }: { order: any; kind: string }) {
  const [url, setUrl] = useState("");
  const [user, setUser] = useState("");
  const [wallet, setWallet] = useState("");
  const [note, setNote] = useState("");
  const connect = useMutation({
    mutationFn: () => api("/rent/connect", { method: "POST", body: JSON.stringify({ order_id: order.id, tonconnect_url: url || "tc://demo" }) }),
    onSuccess: () => setNote("TON Connect сохранён"),
  });
  const transfer = useMutation({
    mutationFn: (destination: "telegram" | "wallet") =>
      api("/nft/transfer", {
        method: "POST",
        body: JSON.stringify({
          order_id: order.id,
          destination,
          username: user,
          wallet_address: wallet,
        }),
      }),
    onSuccess: (d: any) => setNote(d.demo ? `Перевод записан → ${d.target}` : "Передано"),
  });
  if (kind === "nft_buy") {
    return (
      <div className="grid aftercare">
        <div className="tiny">Отправить NFT</div>
        <input placeholder="Telegram username" value={user} onChange={(e) => setUser(e.target.value.replace("@", ""))} />
        <button className="btn ghost block" disabled={transfer.isPending} onClick={() => transfer.mutate("telegram")}>В профиль Telegram</button>
        <input placeholder="TON-кошелёк UQ…" value={wallet} onChange={(e) => setWallet(e.target.value)} />
        <button className="btn ghost block" disabled={transfer.isPending} onClick={() => transfer.mutate("wallet")}>На кошелёк</button>
        {note && <div className="muted">{note}</div>}
        {transfer.error && <div className="err">{(transfer.error as ApiError).message}</div>}
      </div>
    );
  }
  if (kind.endsWith("_rent")) {
    return (
      <div className="grid aftercare">
        <div className="tiny">TON Connect</div>
        <input placeholder="tc:// ссылка с Fragment" value={url} onChange={(e) => setUrl(e.target.value)} />
        <button className="btn ghost block" disabled={connect.isPending} onClick={() => connect.mutate()}>Привязать</button>
        {note && <div className="muted">{note}</div>}
      </div>
    );
  }
  return null;
}

export function AssetPage({ me }: { me: { balance: string; username?: string } }) {
  const { kind = "", address = "" } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const catalog = useQuery({ queryKey: ["catalog"], queryFn: () => api("/catalog") });
  const product = productByKind(catalog.data?.items, kind);
  const [days, setDays] = useState(kind === "nft_buy" ? 1 : 1);
  const [confirm, setConfirm] = useState(false);
  const [done, setDone] = useState<any>(null);
  const quote = useQuery({
    queryKey: ["quote", kind, address, days],
    queryFn: () => api(`/rent/quote?kind=${kind}&address=${encodeURIComponent(address)}&days=${days}`),
    enabled: !!kind && !!address,
  });
  const min = quote.data?.min_quantity || 1;
  const max = quote.data?.max_quantity || 90;
  useEffect(() => {
    if (quote.data?.min_quantity && days < quote.data.min_quantity) {
      setDays(quote.data.min_quantity);
    }
  }, [quote.data?.min_quantity, days]);
  const productId = quote.data?.product_id || product?.id;
  const buy = useMutation({
    mutationFn: () =>
      api("/orders", {
        method: "POST",
        body: JSON.stringify({
          product_id: productId,
          quantity: kind === "nft_buy" ? 1 : days,
          recipient: address,
          nft_address: address,
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
  const after = Number(me.balance) - Number(quote.data?.total || 0);
  const title = prettyName(kind, quote.data?.name, address);
  const isHandle = kind === "username_rent" || kind === "number_rent";
  if (!quote.data) return <div className="asset-page"><div className="skeleton tall" /></div>;
  const presets = Array.from(new Set([min, 7, 14, 30, 60, 90, max]))
    .filter((d) => d >= min && d <= max)
    .sort((a, b) => a - b);
  return (
    <div className="grid asset-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}>
        <ArrowLeft size={16} /> Назад
      </button>
      <div className="panel asset-hero">
        {isHandle ? (
          <div className="handle-hero">{title}</div>
        ) : (
          <GiftArt tone={quote.data.tone} motif={quote.data.motif} name={title} image={quote.data.image} large />
        )}
        {!isHandle ? <h1 className="h1 display">{title}</h1> : null}
        {quote.data.collection_name ? <div className="muted">{quote.data.collection_name}</div> : null}
      </div>
      {kind !== "nft_buy" && (
        <>
          <div className="qty">
            <button type="button" onClick={() => setDays(Math.max(min, days - 1))}><Minus size={16} /></button>
            <b className="display num qty-val">{days} дн.</b>
            <button type="button" onClick={() => setDays(Math.min(max, days + 1))}><Plus size={16} /></button>
          </div>
          <div className="presets">
            {presets.map((d) => (
              <button key={d} className={days === d ? "on" : ""} onClick={() => setDays(d)}>{d} дн.</button>
            ))}
          </div>
        </>
      )}
      <div className="panel pad">
        <div className="between">
          <span className="muted">{kind === "nft_buy" ? "Цена" : "За день"}</span>
          <b>
            {quote.data.compare_at ? <span className="compare">{formatRub(Number(quote.data.compare_at) / Math.max(1, quote.data.quantity))}</span> : null}
            {formatRub(quote.data.unit_price)}
          </b>
        </div>
        <div className="between"><span className="muted">Итого</span><b className="h2 num">{formatRub(quote.data.total)}</b></div>
        <div className="between"><span className="muted">Баланс после</span><span className="num">{formatRub(after)}</span></div>
      </div>
      {buy.error && <div className="err">{(buy.error as ApiError).message}</div>}
      <div className="asset-cta">
        <button className="btn block" disabled={!productId} onClick={() => { haptic("medium"); setConfirm(true); }}>
          {kind === "nft_buy" ? "Купить" : "Арендовать"} за {formatRub(quote.data.total)}
        </button>
      </div>
      {confirm && (
        <div className="sheet open" onClick={() => setConfirm(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2 display">Подтвердить заказ?</h2>
            <div>{title}</div>
            {kind !== "nft_buy" && <div>{days} дней</div>}
            <div className="h2">{formatRub(quote.data.total)}</div>
            <div className="row">
              <button className="btn ghost block" onClick={() => setConfirm(false)}>Отмена</button>
              <button className="btn block" disabled={buy.isPending} onClick={() => buy.mutate()}>Подтвердить</button>
            </div>
          </div>
        </div>
      )}
      {done && (
        <Success
          order={done}
          title={title}
          extra={<Aftercare order={done} kind={kind} />}
        />
      )}
    </div>
  );
}
