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

export function DigitalShop({ group }: { group: "topup" | "games" }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const list = useQuery({
    queryKey: ["digital", group],
    queryFn: () => api(`/digital/catalog?group=${group}`),
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
      <h1 className="h1 display">{group === "games" ? "Игры" : "Пополнения"}</h1>
      <p className="muted lead">{group === "games" ? "Roblox, Minecraft и другие коды." : "Steam, Google Play, App Store, PlayStation — оплата с баланса, код после покупки."}</p>
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
            <div className="muted">{p.region ? `${p.region} · ` : ""}{p.face_value} {p.currency}{p.in_stock ? "" : " · нет в наличии"}</div>
          </div>
          <b className="num">{formatRub(p.price)}</b>
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
  const after = Number(me.balance) - Number(p.price);
  const fields = p.extra_fields || [];
  const missing = fields.some((f: any) => f.required && !(extra[f.key] || "").trim());
  const username = extra.username;
  return (
    <div className="grid product-page">
      <button className="back-link" type="button" onClick={() => nav(-1)}>
        <ArrowLeft size={16} /> Назад
      </button>
      <div className="panel pad grid">
        <div className="tiny">{CAT[p.category] || p.category}</div>
        <h1 className="h1 display">{p.name}</h1>
        <p className="muted lead">{p.description}</p>
        <div className="between"><span className="muted">Номинал</span><b>{p.face_value} {p.currency}</b></div>
        {p.region ? <div className="between"><span className="muted">Регион</span><b>{p.region}</b></div> : null}
        <div className="between"><span className="muted">Наличие</span><b>{p.in_stock ? `${p.stock} шт.` : "Нет"}</b></div>
        <div className="h2 num">{formatRub(p.price)}</div>
      </div>
      {fields.map((f: any) => (
        <label key={f.key} className="tiny">{f.label}
          <input value={extra[f.key] || ""} onChange={(e) => setExtra({ ...extra, [f.key]: e.target.value })} placeholder={f.label} />
        </label>
      ))}
      {username ? <div className="muted">Пополнение на аккаунт: {username}</div> : null}
      <div className="panel pad grid">
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
          <p className="muted">Код появится в «Мои покупки» после выдачи. Деньги уже списаны, повторно не спишем.</p>
          <Link className="btn block" to="/purchases">Мои покупки</Link>
        </div>
      ) : (
        <button
          className="btn block"
          disabled={buy.isPending || !p.in_stock || missing || after < 0}
          onClick={() => { haptic("medium"); setConfirm(true); }}
        >
          {!p.in_stock ? "Нет в наличии" : after < 0 ? "Недостаточно средств" : `Оплатить ${formatRub(p.price)}`}
        </button>
      )}
      {confirm && (
        <div className="sheet open" onClick={() => setConfirm(false)}>
          <div className="panel grid" onClick={(e) => e.stopPropagation()}>
            <h2 className="h2 display">Подтвердить покупку?</h2>
            <div>Товар: {p.name}</div>
            {username ? <div>Аккаунт: {username}</div> : null}
            <div>Цена: {formatRub(p.price)}</div>
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
        <div className="empty">Покупок цифровых товаров пока нет<br /><Link to="/digital" className="btn" style={{ display: "inline-block", marginTop: 12 }}>К пополнениям</Link></div>
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
        {o.extra?.username ? <div className="muted">Получатель: {o.extra.username}</div> : null}
        {o.code ? (
          <>
            <div className="tiny">Ваш код</div>
            <b className="mono h2">{o.code}</b>
            <button className="btn block" onClick={() => { navigator.clipboard.writeText(o.code); setCopied(true); }}>
              {copied ? "Скопировано" : "Скопировать"}
            </button>
          </>
        ) : (
          <p className="muted">Код появится после выдачи.</p>
        )}
      </div>
    </div>
  );
}
