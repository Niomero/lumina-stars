import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Check, Copy } from "lucide-react";
import { api, ApiError } from "./api/client";
import { formatRub } from "./lib/format";
import { haptic } from "./lib/telegram";
import { FilterBar } from "./Filters";

const CAT: Record<string, string> = {
  steam: "Steam",
  google_play: "Google Play",
  app_store: "App Store",
  playstation: "PlayStation",
  xbox: "Xbox",
  nintendo: "Nintendo",
  roblox: "Roblox",
  minecraft: "Minecraft",
  fortnite: "Fortnite",
  valorant: "Valorant",
  spotify: "Spotify",
  other: "Другое",
};

function digitalStatus(s: string) {
  const map: Record<string, string> = {
    pending: "Ожидает",
    processing: "В обработке",
    completed: "Выдан",
    failed: "Ошибка",
    refunded: "Возврат",
  };
  return map[s] || s;
}

function priceLabel(p: any) {
  if (p.amount_mode === "custom") return `от ${formatRub(p.min_amount || 0)}`;
  return formatRub(p.price);
}

export function DigitalShop({ group }: { group?: "topup" | "games" }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [grp, setGrp] = useState(group || "");
  const list = useQuery({
    queryKey: ["digital", grp || "all"],
    queryFn: () => api(`/digital/catalog${grp ? `?group=${grp}` : ""}`),
  });
  const source = list.data?.items || [];
  const items = source.filter((p: any) => {
    if (category && p.category !== category) return false;
    if (q && !(`${p.name} ${p.region} ${p.face_value}`).toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });
  const cats = [
    { id: "", label: "Все" },
    ...Object.entries(CAT)
      .filter(([id]) => source.some((p: any) => p.category === id))
      .map(([id, label]) => ({ id, label })),
  ];
  return (
    <div className="grid">
      <h1 className="h1 display">Digital</h1>
      <p className="muted lead">Коды и пополнения: Steam по логину, Roblox, Minecraft, магазины. Оплата с баланса Lumina.</p>
      {!group && (
        <div className="chips">
          {[["", "Все"], ["topup", "Пополнения"], ["games", "Игры"]].map(([id, label]) => (
            <button key={id || "all"} type="button" className={grp === id ? "on" : ""} onClick={() => { setGrp(id); setCategory(""); }}>
              {label}
            </button>
          ))}
        </div>
      )}
      <FilterBar
        search={q}
        onSearch={setQ}
        categories={cats}
        category={category}
        onCategory={setCategory}
      />
      {list.isLoading && <div className="skeleton" />}
      {items.map((p: any) => (
        <Link key={p.id} to={`/digital/${p.id}`} className="panel product">
          <div className="icon-blob">{(CAT[p.category] || p.category).slice(0, 2)}</div>
          <div style={{ flex: 1 }}>
            <b>{p.name}</b>
            <div className="muted">
              {CAT[p.category] || p.category}
              {p.face_value ? ` · ${p.face_value} ${p.currency}` : ""}
              {p.amount_mode === "custom" ? " · своя сумма" : ""}
              {p.in_stock ? "" : " · нет в наличии"}
            </div>
          </div>
          <b className="num">{priceLabel(p)}</b>
        </Link>
      ))}
      {!list.isLoading && !items.length && <div className="empty">Пока нет предложений в этой категории</div>}
    </div>
  );
}

export function DigitalProductPage({ me }: { me: { balance: string; username?: string } }) {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const product = useQuery({ queryKey: ["digital-item", id], queryFn: () => api(`/digital/products/${id}`) });
  const [extra, setExtra] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const buy = useMutation({
    mutationFn: () =>
      api("/digital/orders", {
        method: "POST",
        body: JSON.stringify({ product_id: Number(id), extra, idempotency_key: crypto.randomUUID() }),
      }),
    onSuccess: () => {
      haptic("success");
      qc.invalidateQueries({ queryKey: ["me"] });
      qc.invalidateQueries({ queryKey: ["digital"] });
    },
    onError: () => haptic("error"),
  });
  if (product.isLoading || !product.data) return <div className="skeleton tall" />;
  const p = product.data;
  const custom = p.amount_mode === "custom";
  const face = Number(String(extra.amount || "").replace(",", "."));
  const markup = Number(p.markup_percent || 0);
  const minA = Number(p.min_amount || 0);
  const maxA = Number(p.max_amount || 0);
  const payable = custom
    ? (Number.isFinite(face) && face > 0 ? Math.round(face * (1 + markup / 100) * 100) / 100 : 0)
    : Number(p.price);
  const after = Number(me.balance) - payable;
  const fields = (p.extra_fields || []).filter((f: any) => f.key !== "amount");
  const missing = fields.some((f: any) => f.required && !(extra[f.key] || "").trim());
  const amountBad = custom && (!Number.isFinite(face) || face <= 0 || (minA > 0 && face < minA) || (maxA > 0 && face > maxA));
  const login = extra.steam_login || extra.username;
  const blocked = buy.isPending || !p.in_stock || missing || amountBad || after < 0 || (custom && !payable);
  return (
    <div className="grid product-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}>
        <ArrowLeft size={16} /> Назад
      </button>
      <div className="panel pad grid">
        <div className="tiny">{CAT[p.category] || p.category}</div>
        <h1 className="h1 display">{p.name}</h1>
        <p className="muted lead">{p.description}</p>
        {!custom && p.face_value ? <div className="between"><span className="muted">Номинал</span><b>{p.face_value} {p.currency}</b></div> : null}
        {p.region ? <div className="between"><span className="muted">Регион</span><b>{p.region}</b></div> : null}
        {!custom ? <div className="between"><span className="muted">Наличие</span><b>{p.in_stock ? (p.delivery_type === "manual" ? "Под заказ" : `${p.stock} шт.`) : "Нет"}</b></div> : null}
        {!custom ? <div className="h2 num">{formatRub(p.price)}</div> : <div className="muted">Комиссия {markup}%. Минимум {formatRub(minA)}{maxA ? ` · максимум ${formatRub(maxA)}` : ""}</div>}
      </div>
      {fields.map((f: any) => (
        <label key={f.key} className="tiny">{f.label}
          <input value={extra[f.key] || ""} onChange={(e) => setExtra({ ...extra, [f.key]: e.target.value })} placeholder={f.label} />
        </label>
      ))}
      {custom && (
        <label className="tiny">Сумма пополнения, ₽
          <input
            inputMode="decimal"
            value={extra.amount || ""}
            onChange={(e) => setExtra({ ...extra, amount: e.target.value.replace(",", ".") })}
            placeholder="Например 500"
          />
        </label>
      )}
      {login ? <div className="muted">Пополнение на аккаунт: {login}</div> : null}
      <div className="panel pad grid">
        {custom && payable > 0 ? <div className="between"><span className="muted">К оплате</span><b className="h2 num">{formatRub(payable)}</b></div> : null}
        <div className="between"><span className="muted">Баланс</span><b>{formatRub(me.balance)}</b></div>
        <div className="between"><span className="muted">После оплаты</span><span className={after < 0 ? "err" : ""}>{formatRub(after)}</span></div>
      </div>
      {buy.error && <div className="err">{(buy.error as ApiError).message}</div>}
      {buy.data?.code ? (
        <div className="panel pad grid">
          <div className="tiny">Ваш код</div>
          <b className="mono h2">{buy.data.code}</b>
          <button className="btn block" onClick={() => { navigator.clipboard.writeText(buy.data.code); setCopied(true); }}>
            {copied ? <><Check size={16} /> Скопировано</> : <><Copy size={16} /> Скопировать</>}
          </button>
          <Link className="btn ghost block" to="/purchases">Мои покупки</Link>
        </div>
      ) : buy.data?.status === "processing" ? (
        <div className="panel pad grid">
          <b>Заказ принят</b>
          <p className="muted">Пополнение обработаем на указанный логин. Статус — в «Мои покупки». Деньги уже списаны.</p>
          <Link className="btn block" to="/purchases">Мои покупки</Link>
        </div>
      ) : (
        <button
          className="btn block"
          disabled={blocked}
          onClick={() => { haptic("medium"); setConfirm(true); }}
        >
          {!p.in_stock ? "Нет в наличии" : amountBad ? "Укажите сумму" : after < 0 ? "Недостаточно средств" : `Оплатить ${formatRub(payable || p.price)}`}
        </button>
      )}
      {confirm && (
        <div className="sheet open" onClick={() => setConfirm(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2 display">Подтвердить покупку?</h2>
            <div>Товар: {p.name}</div>
            {login ? <div>Аккаунт: {login}</div> : null}
            {custom ? <div>Пополнение: {formatRub(face)}</div> : null}
            <div>К оплате: {formatRub(payable)}</div>
            <div>Баланс после: {formatRub(after)}</div>
            <div className="row">
              <button className="btn ghost block" onClick={() => setConfirm(false)}>Отмена</button>
              <button className="btn block" disabled={buy.isPending} onClick={() => { setConfirm(false); buy.mutate(); }}>Оплатить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function MyPurchases() {
  const list = useQuery({ queryKey: ["digital-orders"], queryFn: () => api("/digital/orders") });
  return (
    <div className="grid">
      <h1 className="h1 display">Мои покупки</h1>
      {(list.data?.items || []).map((o: any) => (
        <Link key={o.public_id} to={`/purchases/${o.public_id}`} className="panel between pad">
          <div>
            <b>{o.product_name}</b>
            <div className="muted">{o.public_id} · {o.created_at ? new Date(o.created_at).toLocaleString("ru") : ""}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <b>{formatRub(o.price)}</b>
            <div className="muted">{digitalStatus(o.status)}</div>
          </div>
        </Link>
      ))}
      {!list.isLoading && !(list.data?.items || []).length && (
        <div className="empty">Покупок цифровых товаров пока нет<br /><Link to="/digital" className="btn" style={{ display: "inline-block", marginTop: 12 }}>В Digital</Link></div>
      )}
    </div>
  );
}

export function PurchaseDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [copied, setCopied] = useState(false);
  const order = useQuery({ queryKey: ["digital-order", id], queryFn: () => api(`/digital/orders/${id}`) });
  if (!order.data) return <div className="skeleton" />;
  const o = order.data;
  return (
    <div className="grid product-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}><ArrowLeft size={16} /> Назад</button>
      <div className="panel pad grid">
        <div className="tiny">{o.public_id}</div>
        <h1 className="h1 display">{o.product_name}</h1>
        <div className="muted">{digitalStatus(o.status)}</div>
        <b>{formatRub(o.price)}</b>
        {o.extra?.steam_login ? <div className="muted">Steam логин: {o.extra.steam_login}</div> : null}
        {o.extra?.username ? <div className="muted">Получатель: {o.extra.username}</div> : null}
        {o.extra?.amount ? <div className="muted">Сумма пополнения: {formatRub(o.extra.amount)}</div> : null}
        {o.code ? (
          <>
            <div className="tiny">Ваш код</div>
            <b className="mono h2">{o.code}</b>
            <button className="btn block" onClick={() => { navigator.clipboard.writeText(o.code); setCopied(true); }}>
              {copied ? "Скопировано" : "Скопировать"}
            </button>
          </>
        ) : (
          <p className="muted">{o.status === "processing" ? "Заказ в обработке. Код или зачисление появятся после выдачи." : "Код появится после выдачи."}</p>
        )}
      </div>
    </div>
  );
}