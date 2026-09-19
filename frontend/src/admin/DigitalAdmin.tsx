import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import { formatRub, when } from "../lib/format";

type Me = { role: string };
const canWrite = (role: string) => ["ADMIN", "SUPERADMIN"].includes(role);

function Err({ e }: { e: unknown }) {
  if (!e) return null;
  return <div className="err">{(e as ApiError).message || "Ошибка"}</div>;
}

const CATS: [string, string][] = [
  ["steam", "Steam"],
  ["google_play", "Google Play"],
  ["app_store", "App Store"],
  ["playstation", "PlayStation"],
  ["xbox", "Xbox"],
  ["nintendo", "Nintendo"],
  ["roblox", "Roblox"],
  ["minecraft", "Minecraft"],
  ["other", "Другое"],
];

const emptyForm = {
  name: "",
  description: "",
  category: "steam",
  group: "topup",
  region: "RU",
  currency: "RUB",
  face_value: "",
  price: "",
  delivery_type: "code",
  needUser: false,
};

function ProductCard({ p, write }: { p: any; write: boolean }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [codes, setCodes] = useState("");
  const [price, setPrice] = useState(String(p.price));
  const patch = useMutation({
    mutationFn: (body: object) => api(`/admin/digital/${p.id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-digital"] }),
  });
  const upload = useMutation({
    mutationFn: () => api(`/admin/digital/${p.id}/codes`, { method: "POST", body: JSON.stringify({ codes }) }),
    onSuccess: () => {
      setCodes("");
      qc.invalidateQueries({ queryKey: ["adm-digital"] });
      qc.invalidateQueries({ queryKey: ["adm-codes", p.id] });
    },
  });
  const list = useQuery({
    queryKey: ["adm-codes", p.id],
    enabled: open,
    queryFn: () => api(`/admin/digital/${p.id}/codes`),
  });
  return (
    <div className="panel pad grid">
      <div className="between">
        <div>
          <b>{p.name}</b>
          <div className="muted">{p.category_label || p.category} · {p.group === "games" ? "Игры" : "Пополнения"} · {p.region || "—"}</div>
        </div>
        <span className={`badge ${p.enabled ? "ok" : "bad"}`}>{p.enabled ? "Вкл" : "Выкл"}</span>
      </div>
      <div className="row">
        <div className="panel pad" style={{ flex: 1 }}><div className="tiny">Цена</div><b>{formatRub(p.price)}</b></div>
        <div className="panel pad" style={{ flex: 1 }}><div className="tiny">Сток</div><b>{p.stock}</b></div>
        <div className="panel pad" style={{ flex: 1 }}><div className="tiny">Продано</div><b>{p.sold ?? 0}</b></div>
      </div>
      {write && (
        <>
          <div className="row">
            <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
            <button className="btn ghost" disabled={patch.isPending} onClick={() => patch.mutate({ price })}>Цена</button>
            <button className="btn ghost" disabled={patch.isPending} onClick={() => patch.mutate({ enabled: !p.enabled })}>
              {p.enabled ? "Выкл" : "Вкл"}
            </button>
          </div>
          <textarea rows={4} placeholder="Коды, по одному в строке" value={codes} onChange={(e) => setCodes(e.target.value)} />
          <Err e={upload.error || patch.error} />
          <button className="btn ghost" disabled={!codes.trim() || upload.isPending} onClick={() => upload.mutate()}>
            Загрузить коды
          </button>
        </>
      )}
      <button className="btn ghost sm" type="button" onClick={() => setOpen(!open)}>{open ? "Скрыть коды" : "Показать коды"}</button>
      {open && (list.data?.items || []).map((c: any) => (
        <div key={c.id} className="between">
          <span className="mono">{c.masked}</span>
          <span className="muted">{c.status}</span>
        </div>
      ))}
      {open && !(list.data?.items || []).length && !list.isLoading && <div className="muted">Кодов нет</div>}
    </div>
  );
}

export function DigitalAdmin({ me }: { me: Me }) {
  const qc = useQueryClient();
  const write = canWrite(me.role);
  const [tab, setTab] = useState<"products" | "orders">("products");
  const [form, setForm] = useState(emptyForm);
  const products = useQuery({ queryKey: ["adm-digital"], queryFn: () => api("/admin/digital") });
  const orders = useQuery({ queryKey: ["adm-dorders"], queryFn: () => api("/admin/digital-orders") });
  const create = useMutation({
    mutationFn: () => {
      const extra = form.needUser || form.category === "roblox"
        ? [{ key: "username", label: form.category === "roblox" ? "Roblox Username" : "Username", required: true }]
        : form.category === "minecraft"
          ? [{ key: "username", label: "Minecraft username", required: false }]
          : [];
      return api("/admin/digital", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          category: form.category,
          group: form.group,
          region: form.region,
          currency: form.currency,
          face_value: form.face_value,
          price: form.price,
          delivery_type: form.delivery_type,
          extra_fields: extra,
        }),
      });
    },
    onSuccess: () => {
      setForm(emptyForm);
      qc.invalidateQueries({ queryKey: ["adm-digital"] });
    },
  });
  const [fulfill, setFulfill] = useState<Record<string, string>>({});
  const sendCode = useMutation({
    mutationFn: ({ id, code }: { id: string; code: string }) =>
      api(`/admin/digital-orders/${id}/fulfill`, { method: "POST", body: JSON.stringify({ code }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["adm-dorders"] }),
  });
  return (
    <div className="grid">
      <h1 className="h1 display">Digital</h1>
      <div className="chips">
        <button className={tab === "products" ? "on" : ""} onClick={() => setTab("products")}>Товары</button>
        <button className={tab === "orders" ? "on" : ""} onClick={() => setTab("orders")}>Заказы</button>
      </div>
      {tab === "products" && write && (
        <div className="panel pad grid">
          <div className="tiny">Новый товар</div>
          <input placeholder="Название" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Описание" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <div className="chips">
            {CATS.map(([k, l]) => (
              <button key={k} className={form.category === k ? "on" : ""} onClick={() => setForm({ ...form, category: k, group: ["roblox", "minecraft"].includes(k) ? "games" : "topup" })}>{l}</button>
            ))}
          </div>
          <div className="chips">
            <button className={form.group === "topup" ? "on" : ""} onClick={() => setForm({ ...form, group: "topup" })}>Пополнения</button>
            <button className={form.group === "games" ? "on" : ""} onClick={() => setForm({ ...form, group: "games" })}>Игры</button>
            <button className={form.delivery_type === "code" ? "on" : ""} onClick={() => setForm({ ...form, delivery_type: "code" })}>Код</button>
            <button className={form.delivery_type === "manual" ? "on" : ""} onClick={() => setForm({ ...form, delivery_type: "manual" })}>Вручную</button>
          </div>
          <div className="row">
            <input placeholder="Регион" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
            <input placeholder="Номинал" value={form.face_value} onChange={(e) => setForm({ ...form, face_value: e.target.value })} />
          </div>
          <input inputMode="decimal" placeholder="Цена ₽" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
          <label className="tiny" style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input type="checkbox" checked={form.needUser} onChange={(e) => setForm({ ...form, needUser: e.target.checked })} />
            Запросить username перед покупкой
          </label>
          <Err e={create.error} />
          <button className="btn block" disabled={!form.name.trim() || !form.price || create.isPending} onClick={() => create.mutate()}>Создать</button>
        </div>
      )}
      {tab === "products" && (products.data?.items || []).map((p: any) => (
        <ProductCard key={p.id} p={p} write={write} />
      ))}
      {tab === "products" && !products.isLoading && !(products.data?.items || []).length && <div className="empty">Товаров нет</div>}
      {tab === "orders" && (orders.data?.items || []).map((o: any) => (
        <div key={o.public_id} className="panel pad grid">
          <div className="between">
            <div>
              <b>{o.product_name}</b>
              <div className="muted">{o.public_id} · {o.user?.username ? `@${o.user.username}` : o.user?.first_name || o.user_id} · {when(o.created_at)}</div>
            </div>
            <span className="badge">{o.status}</span>
          </div>
          <b>{formatRub(o.price)}</b>
          {o.extra?.username ? <div className="muted">Получатель: {o.extra.username}</div> : null}
          {write && o.status === "processing" && (
            <>
              <input placeholder="Код для выдачи" value={fulfill[o.public_id] || ""} onChange={(e) => setFulfill({ ...fulfill, [o.public_id]: e.target.value })} />
              <Err e={sendCode.error} />
              <button className="btn" disabled={sendCode.isPending || !(fulfill[o.public_id] || "").trim()} onClick={() => sendCode.mutate({ id: o.public_id, code: fulfill[o.public_id] })}>
                Выдать
              </button>
            </>
          )}
        </div>
      ))}
      {tab === "orders" && !orders.isLoading && !(orders.data?.items || []).length && <div className="empty">Digital-заказов нет</div>}
      {me.role === "MANAGER" && <p className="muted">Просмотр. Изменения — у администратора.</p>}
      <Link to="/admin" className="subtle">На дашборд</Link>
    </div>
  );
}
